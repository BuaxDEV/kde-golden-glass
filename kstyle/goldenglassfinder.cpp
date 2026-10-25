/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "goldenglassfinder.h"

#include "goldenglass_tokens.h"
#include "goldenglasshelper.h"
#include "goldenglassstyleconfigdata.h"
#include "goldenglasstrafficlight.h"

#include <KConfig>
#include <KConfigGroup>
#include <KSharedConfig>

#include <QAbstractScrollArea>
#include <QAction>
#include <QActionGroup>
#include <QApplication>
#include <QDebug>
#include <QDir>
#include <QDockWidget>
#include <QFile>
#include <QFileInfo>
#include <QGraphicsObject>
#include <QGraphicsScene>
#include <QGraphicsView>
#include <QGuiApplication>
#include <QHoverEvent>
#include <QItemSelectionModel>
#include <QKeyEvent>
#include <QLayout>
#include <QLineEdit>
#include <QListView>
#include <QMainWindow>
#include <QMenuBar>
#include <QMouseEvent>
#include <QPainter>
#include <QPainterPath>
#include <QRegularExpression>
#include <QResizeEvent>
#include <QSaveFile>
#include <QStandardPaths>
#include <QTimer>
#include <QToolBar>
#include <QToolButton>
#include <QVariantAnimation>
#include <QtMath>

#include <dlfcn.h>
#include <sys/xattr.h>

namespace GoldenGlass
{

namespace
{
//* version of the Finder defaults written for Dolphin (goldenglassrc [Finder])
constexpr int DolphinDefaultsVersion = 1;

//* Dolphin's main toolbar laid out as Finder's: ‹ › title … views, group by,
//* split and menu, search. Separators split the capsules.
const char DolphinToolBar[] = R"(<ToolBar noMerge="1" name="mainToolBar" >
        <text context="@title:menu">Main Toolbar</text>
        <Action name="go_back" />
        <Action name="go_forward" />
        <Separator name="separator_finder_0" />
        <Action name="url_navigators" />
        <Separator name="separator_finder_1" />
        <Action name="icons" />
        <Action name="details" />
        <Action name="compact" />
        <Separator name="separator_finder_2" />
        <Action name="group_by" />
        <Separator name="separator_finder_3" />
        <Action name="split_view" />
        <Action name="hamburger_menu" />
        <Separator name="separator_finder_4" />
        <Action name="toggle_search" />
    </ToolBar>)";

//* versión de un ui.rc (atributo version de <gui>); -1 si no la tiene
int uiRcVersion(const QString &xml)
{
    static const QRegularExpression version(QStringLiteral("<gui\\b[^>]*\\bversion=\"(\\d+)\""));
    const QRegularExpressionMatch match = version.match(xml);
    return match.hasMatch() ? match.captured(1).toInt() : -1;
}

//* las propiedades de las acciones (atajos, prioridades) del ui.rc anterior
//* pasan al nuevo, como hace KXMLGUI al descartar una copia desfasada
QString mergeActionProperties(QString xml, const QString &previous)
{
    static const QRegularExpression block(QStringLiteral("<ActionProperties\\b.*?</ActionProperties>"), QRegularExpression::DotMatchesEverythingOption);
    static const QRegularExpression action(QStringLiteral("<Action\\b[^>]*\\bname=\"([^\"]+)\"[^>]*/>"));
    const QRegularExpressionMatch oldBlock = block.match(previous);
    if (!oldBlock.hasMatch()) {
        return xml;
    }
    const QRegularExpressionMatch newBlock = block.match(xml);
    if (!newBlock.hasMatch()) {
        const qsizetype end = xml.lastIndexOf(QLatin1String("</gui>"));
        if (end >= 0) {
            xml.insert(end, oldBlock.captured(0) + QLatin1Char('\n'));
        }
        return xml;
    }

    QString merged = newBlock.captured(0);
    auto oldActions = action.globalMatch(oldBlock.captured(0));
    while (oldActions.hasNext()) {
        const QRegularExpressionMatch oldAction = oldActions.next();
        const QRegularExpression same(QStringLiteral("<Action\\b[^>]*\\bname=\"%1\"[^>]*/>").arg(QRegularExpression::escape(oldAction.captured(1))));
        const QRegularExpressionMatch current = same.match(merged);
        if (current.hasMatch()) {
            merged.replace(current.capturedStart(), current.capturedLength(), oldAction.captured(0));
        } else {
            merged.insert(merged.lastIndexOf(QLatin1String("</ActionProperties>")), oldAction.captured(0) + QLatin1Char('\n'));
        }
    }
    xml.replace(newBlock.capturedStart(), newBlock.capturedLength(), merged);
    return xml;
}

//* saca de su barra un widget añadido con insertWidget(). La acción (dueña
//* del widget) se borra más tarde: unpolish() se llama mientras Qt recorre
//* todos los widgets
void removeToolBarWidget(QWidget *widget)
{
    if (!widget) {
        return;
    }
    widget->setObjectName(QString());
    auto toolBar = qobject_cast<QToolBar *>(widget->parentWidget());
    const auto actions = toolBar ? toolBar->actions() : QList<QAction *>();
    for (QAction *action : actions) {
        if (toolBar->widgetForAction(action) == widget) {
            // la barra devuelve el widget, oculto, a su acción
            toolBar->removeAction(action);
            action->deleteLater();
            return;
        }
    }
    widget->hide();
    widget->deleteLater();
}

QString actionName(const QToolButton *button)
{
    if (QAction *action = button->defaultAction()) {
        return action->objectName();
    }
    return button->objectName();
}

//* KItemListWidget::alternateBackground() const, exported by Dolphin's
//* library: which rows Dolphin stripes (it restarts in every group). The
//* style is loaded into Dolphin, so the symbol is there; elsewhere, null.
using AlternateBackground = bool (*)(const void *);
AlternateBackground alternateBackgroundFunction()
{
    static const auto function = reinterpret_cast<AlternateBackground>(dlsym(RTLD_DEFAULT, "_ZNK15KItemListWidget19alternateBackgroundEv"));
    return function;
}

//* QAbstractScrollArea::setViewportMargins is protected
struct ScrollAreaAccess : QAbstractScrollArea {
    using QAbstractScrollArea::setViewportMargins;
};

//* KIO's breadcrumb widgets live in the KDEPrivate namespace
bool isKioPrivate(const QObject *object, const char *className)
{
    return object->inherits(QByteArray("KDEPrivate::") + className) || object->inherits(className);
}

//* menus that open on click show ⌄; delayed ones (‹ › history) don't, as in Finder
bool showsMenuArrow(const QStyleOptionToolButton *option)
{
    const auto features = option->features;
    return (features & QStyleOptionToolButton::MenuButtonPopup)
        || ((features & QStyleOptionToolButton::HasMenu) && !(features & QStyleOptionToolButton::PopupDelay));
}

QRectF lerp(const QRectF &from, const QRectF &to, qreal t)
{
    return QRectF(from.x() + (to.x() - from.x()) * t,
                  from.y() + (to.y() - from.y()) * t,
                  from.width() + (to.width() - from.width()) * t,
                  from.height() + (to.height() - from.height()) * t);
}

bool isDark(const QPalette &palette)
{
    return qGray(palette.color(QPalette::Window).rgb()) < 128;
}

//* starts (or retargets) an animation from its current value
void animateTo(QVariantAnimation *animation, qreal to, int duration, const QEasingCurve &curve)
{
    const qreal from = animation->currentValue().isValid() ? animation->currentValue().toReal() : to;
    animation->stop();
    animation->setStartValue(from);
    animation->setEndValue(to);
    animation->setDuration(duration);
    animation->setEasingCurve(curve);
    animation->start();
}

QEasingCurve springCurve()
{
    QEasingCurve curve(QEasingCurve::OutBack);
    curve.setOvershoot(Tokens::FinderReleaseOvershoot);
    return curve;
}
}

//____________________________________________________________________
Finder::Finder(Helper &helper, std::function<bool(const QWidget *)> isTranslucent, std::function<void(QWidget *)> updateBlur, QObject *parent)
    : QObject(parent)
    , _helper(helper)
    , _isTranslucent(std::move(isTranslucent))
    , _updateBlur(std::move(updateBlur))
{
}

//____________________________________________________________________
Finder::~Finder() = default;

//____________________________________________________________________
void Finder::loadConfiguration()
{
    // the app list matches Wayland app ids; at style creation only the
    // executable name is known (KAboutData sets the desktop file name later)
    const QStringList apps = StyleConfigData::integratedTitleBarApps();
    const QString name = QCoreApplication::applicationName();
    const QString desktopName = QGuiApplication::desktopFileName();
    _active =
        !name.isEmpty() && (apps.contains(name) || apps.contains(QStringLiteral("org.kde.") + name) || (!desktopName.isEmpty() && apps.contains(desktopName)));
    if (!_active) {
        _decorationIsOurs = false;
        return;
    }

    // without our decoration KWin keeps the title bar: no traffic lights here
    KSharedConfig::Ptr kwinConfig = KSharedConfig::openConfig(QStringLiteral("kwinrc"));
    kwinConfig->reparseConfiguration();
    const KConfigGroup decoration = kwinConfig->group(QStringLiteral("org.kde.kdecoration2"));
    _decorationIsOurs = decoration.readEntry("library", QString()) == QLatin1String("org.goldenglass.decoration");
}

//____________________________________________________________________
void Finder::polishApplication(QApplication *)
{
    if (_active && QCoreApplication::applicationName() == QLatin1String("dolphin")) {
        applyDolphinDefaults();
    }
}

//____________________________________________________________________
void Finder::polishPalette(QPalette &palette) const
{
    if (!_active) {
        return;
    }
    // Dolphin fills the alternate rows edge to edge; the rounded stripes are
    // painted behind the items (paintStripes)
    for (const auto group : {QPalette::Active, QPalette::Inactive, QPalette::Disabled}) {
        palette.setColor(group, QPalette::AlternateBase, Qt::transparent);
    }
}

//____________________________________________________________________
void Finder::polish(QWidget *widget)
{
    if (!_active || !widget) {
        return;
    }

    if (auto toolBar = qobject_cast<QToolBar *>(widget)) {
        if (isFinderToolBar(toolBar)) {
            if (!toolBar->property("_goldenglass_toolButtonStyle").isValid()) {
                toolBar->setProperty("_goldenglass_toolButtonStyle", int(toolBar->toolButtonStyle()));
            }
            toolBar->setAttribute(Qt::WA_Hover);
            toolBar->setMouseTracking(true);
            toolBar->setToolButtonStyle(Qt::ToolButtonIconOnly);
            toolBar->removeEventFilter(this);
            toolBar->installEventFilter(this);
            updateToolBarMargins(toolBar->window());
        }

    } else if (qobject_cast<QDockWidget *>(widget) && qobject_cast<QMainWindow *>(widget->parentWidget())) {
        // the toolbar follows the width of the sidebars; the places one keeps
        // Finder's distance from the selection pill to its edges
        if (widget->objectName() == QLatin1String("placesDock")) {
            if (!widget->property("_goldenglass_margins").isValid()) {
                widget->setProperty("_goldenglass_margins", QVariant::fromValue(widget->contentsMargins()));
            }
            const int margin = Tokens::FinderSidebarMargin;
            widget->setContentsMargins(margin, 2, margin, 2);
        }
        widget->removeEventFilter(this);
        widget->installEventFilter(this);

    } else if (widget->inherits("KUrlNavigator")) {
        // Dolphin moves its navigators into the toolbar after creating them
        widget->removeEventFilter(this);
        widget->installEventFilter(this);
        updateNavigator(widget);

    } else if (widget->inherits("Search::Bar")) {
        widget->removeEventFilter(this);
        widget->installEventFilter(this);
        QPointer<QWidget> bar(widget);
        QMetaObject::invokeMethod(
            this,
            [this, bar]() {
                if (bar) {
                    updateSearch(bar);
                }
            },
            Qt::QueuedConnection);

    } else if (widget->inherits("KFilePlacesView")) {
        auto view = static_cast<QAbstractScrollArea *>(widget);
        // selected places keep the text color: the selection is a gray pill
        QPalette palette(view->palette());
        for (const auto group : {QPalette::Active, QPalette::Inactive}) {
            palette.setColor(group, QPalette::HighlightedText, palette.color(group, QPalette::WindowText));
        }
        view->setPalette(palette);
        // KIO draws the icon 4 px into the item (and the text relative to the
        // viewport): a viewport margin puts both inside the pill, which is
        // painted underneath, on the view itself
        const int margin = qMax(0, Tokens::FinderSidebarIconPadding - 4);
        static_cast<ScrollAreaAccess *>(view)->setViewportMargins(margin, 0, margin, 0);
        view->removeEventFilter(this);
        view->installEventFilter(this);
        view->viewport()->removeEventFilter(this);
        view->viewport()->installEventFilter(this);

    } else if (widget->inherits("KItemListContainer")) {
        auto container = static_cast<QAbstractScrollArea *>(widget);
        // the view reaches the window edges, without frame: its background
        // also goes under the (overlay) scrollbars
        if (!container->property("_goldenglass_frameShape").isValid()) {
            container->setProperty("_goldenglass_frameShape", int(container->frameShape()));
        }
        container->setFrameShape(QFrame::NoFrame);
        container->removeEventFilter(this);
        container->installEventFilter(this);
        if (auto graphicsView = qobject_cast<QGraphicsView *>(container->viewport())) {
            graphicsView->viewport()->removeEventFilter(this);
            graphicsView->viewport()->installEventFilter(this);
        }
    }
}

//____________________________________________________________________
void Finder::unpolish(QWidget *widget)
{
    if (!widget) {
        return;
    }
    widget->removeEventFilter(this);

    // another style: undo what polish changed. The toolbar gets back its own
    // layout (QToolBar resets the margins on the style change); además
    // recupera su estilo de botones y pierde el espaciador y el buscador
    if (auto toolBar = qobject_cast<QToolBar *>(widget)) {
        if (const QVariant style = toolBar->property("_goldenglass_toolButtonStyle"); style.isValid()) {
            toolBar->setToolButtonStyle(Qt::ToolButtonStyle(style.toInt()));
            toolBar->setProperty("_goldenglass_toolButtonStyle", QVariant());
        }
        removeToolBarWidget(toolBar->findChild<QWidget *>(QStringLiteral("goldenglass_finder_lead"), Qt::FindDirectChildrenOnly));
        for (auto it = _searchFields.begin(); it != _searchFields.end();) {
            if (it.value() && it.value()->parentWidget() == toolBar) {
                removeToolBarWidget(it.value());
                it = _searchFields.erase(it);
            } else {
                ++it;
            }
        }
        toolBar->setProperty("_goldenglass_searchShown", QVariant());

    } else if (widget->property("_goldenglass_finderTitle").toBool()) {
        // la ruta: su fuente y los botones ocultados para el título
        widget->setProperty("_goldenglass_finderTitle", QVariant());
        const QVariant font = widget->property("_goldenglass_finderFont");
        widget->setFont(font.isValid() ? font.value<QFont>() : QFont());
        widget->setProperty("_goldenglass_finderFont", QVariant());
        const auto children = widget->findChildren<QWidget *>(Qt::FindDirectChildrenOnly);
        for (QWidget *child : children) {
            if (child->property("_goldenglass_finderHidden").toBool()) {
                child->setProperty("_goldenglass_finderHidden", QVariant());
                child->show();
            }
            if (child->property("_goldenglass_finderTransparent").toBool()) {
                child->setProperty("_goldenglass_finderTransparent", QVariant());
                child->setAttribute(Qt::WA_TransparentForMouseEvents, false);
            }
        }
        // KIO vuelve a decidir qué botones caben
        QCoreApplication::postEvent(widget, new QResizeEvent(widget->size(), widget->size()));

    } else if (const QVariant margins = widget->property("_goldenglass_margins"); margins.isValid()) {
        widget->setContentsMargins(margins.value<QMargins>());
        widget->setProperty("_goldenglass_margins", QVariant());

    } else if (widget->inherits("KFilePlacesView")) {
        auto view = static_cast<QAbstractScrollArea *>(widget);
        static_cast<ScrollAreaAccess *>(view)->setViewportMargins(0, 0, 0, 0);
        view->setPalette(QPalette());
        view->viewport()->removeEventFilter(this);

    } else if (widget->inherits("KItemListContainer")) {
        auto container = static_cast<QAbstractScrollArea *>(widget);
        if (const QVariant shape = container->property("_goldenglass_frameShape"); shape.isValid()) {
            container->setFrameShape(QFrame::Shape(shape.toInt()));
            container->setProperty("_goldenglass_frameShape", QVariant());
        }
        if (auto graphicsView = qobject_cast<QGraphicsView *>(container->viewport())) {
            graphicsView->viewport()->removeEventFilter(this);
        }

    } else if (widget->property("_goldenglass_searchLayout").toBool()) {
        // the search bar gets its field back (Filter stays in the second row)
        if (auto editor = qobject_cast<QLineEdit *>(widget->property("_goldenglass_searchEditor").value<QObject *>())) {
            editor->setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX);
            editor->removeEventFilter(this);
            editor->setProperty("_goldenglass_searchSource", QVariant());
        }
        const auto buttons = widget->findChildren<QToolButton *>();
        for (QToolButton *button : buttons) {
            if (button->property("_goldenglass_searchHidden").toBool()) {
                button->setProperty("_goldenglass_searchHidden", QVariant());
                button->show();
            }
        }
        widget->setProperty("_goldenglass_searchLayout", QVariant());
        _searchBars.removeAll(widget);
        removeToolBarWidget(_searchFields.take(widget));
    }
}

//____________________________________________________________________
bool Finder::isFinderToolBar(const QWidget *widget) const
{
    auto toolBar = qobject_cast<const QToolBar *>(widget);
    if (!_active || !toolBar || toolBar->isFloating() || toolBar->orientation() != Qt::Horizontal) {
        return false;
    }
    auto mainWindow = qobject_cast<const QMainWindow *>(toolBar->parentWidget());
    return mainWindow && toolBar->objectName() == QLatin1String("mainToolBar") && mainWindow->toolBarArea(toolBar) == Qt::TopToolBarArea;
}

//____________________________________________________________________
bool Finder::isFinderToolButton(const QWidget *widget) const
{
    return qobject_cast<const QToolButton *>(widget) && widget->objectName() != QLatin1String("qt_toolbar_ext_button")
        && isFinderToolBar(widget->parentWidget());
}

//____________________________________________________________________
bool Finder::isFinderNavigator(const QWidget *widget) const
{
    if (!_active || !widget || !widget->inherits("KUrlNavigator")) {
        return false;
    }
    for (const QWidget *parent = widget->parentWidget(); parent; parent = parent->parentWidget()) {
        if (qobject_cast<const QToolBar *>(parent)) {
            return isFinderToolBar(parent);
        }
    }
    return false;
}

//____________________________________________________________________
bool Finder::isIntegratedWindow(const QWidget *window) const
{
    // same conditions as the decoration (SettingsProvider::internalSettings):
    // an app of the list and a window exporting its menu bar
    if (!_active || !_decorationIsOurs) {
        return false;
    }
    auto mainWindow = qobject_cast<const QMainWindow *>(window);
    if (!mainWindow) {
        return false;
    }
    auto menuBar = qobject_cast<const QMenuBar *>(mainWindow->menuWidget());
    return menuBar && menuBar->isNativeMenuBar();
}

//____________________________________________________________________
int Finder::sidebarItemHeight(const QWidget *widget) const
{
    // Finder's row pitch
    if (!_active || !widget || !widget->inherits("KFilePlacesView")) {
        return -1;
    }
    return Tokens::FinderSidebarRowHeight;
}

//____________________________________________________________________
int Finder::toolBarItemMargin() const
{
    // centers the capsules in the first row (QToolBar adds the frame width)
    return qMax(0, (Tokens::FinderToolBarHeight - Tokens::FinderCapsuleHeight) / 2 - 2);
}

//____________________________________________________________________
Finder::Group Finder::groupFor(const QToolButton *button) const
{
    Group result;
    auto toolBar = qobject_cast<QToolBar *>(button->parentWidget());
    if (!toolBar) {
        return result;
    }

    QList<QToolButton *> current;
    bool found = false;
    const auto flush = [&]() {
        if (!found && current.contains(const_cast<QToolButton *>(button))) {
            result.buttons = current;
            found = true;
        }
        current.clear();
    };

    const auto actions = toolBar->actions();
    for (QAction *action : actions) {
        if (!action->isVisible()) {
            continue;
        }
        QWidget *widget = toolBar->widgetForAction(action);
        if (!widget || widget->isHidden()) {
            continue;
        }
        auto toolButton = qobject_cast<QToolButton *>(widget);
        if (action->isSeparator() || !toolButton) {
            flush();
            continue;
        }
        current.append(toolButton);
    }
    flush();

    if (result.buttons.isEmpty()) {
        return result;
    }

    // the capsule spans the buttons and is centered in the row
    QRect span;
    bool allCheckable = result.buttons.size() > 1;
    QStringList names;
    for (QToolButton *toolButton : std::as_const(result.buttons)) {
        span = span.united(toolButton->geometry());
        allCheckable = allCheckable && toolButton->isCheckable();
        names.append(actionName(toolButton));
    }
    const int height = Tokens::FinderCapsuleHeight;
    result.rect = QRect(span.left(), span.center().y() - height / 2 + (span.height() % 2 ? 0 : 1) - 1, span.width(), height);
    result.segmented = allCheckable;
    result.navigation = names.contains(QLatin1String("go_back")) || names.contains(QLatin1String("go_forward"));
    return result;
}

//____________________________________________________________________
QSize Finder::toolButtonSize(const QStyleOptionToolButton *option, const QWidget *widget) const
{
    auto button = qobject_cast<const QToolButton *>(widget);
    const bool hamburger = button && actionName(button) == QLatin1String("hamburger_menu");
    const bool hasMenu = option && showsMenuArrow(option) && !hamburger;

    // the search field takes the place of the magnifier
    if (button && actionName(button) == QLatin1String("toggle_search") && button->parentWidget()
        && button->parentWidget()->property("_goldenglass_searchShown").toBool()) {
        return QSize(0, Tokens::FinderCapsuleHeight);
    }

    int width = Tokens::FinderButtonWidth + (hasMenu ? Tokens::FinderMenuArrow : 0);
    if (button && !hasMenu && groupFor(button).buttons.size() == 1) {
        // a button on its own is a circle (search)
        width = Tokens::FinderCapsuleHeight;
    }
    if (option && option->icon.isNull() && !option->text.isEmpty()) {
        // a button without icon shows its text
        width = qMax(width, option->fontMetrics.horizontalAdvance(option->text) + Tokens::FinderCapsuleHeight);
    }
    return QSize(width, Tokens::FinderCapsuleHeight);
}

//____________________________________________________________________
QColor Finder::token(unsigned int light, unsigned int dark, const QPalette &palette) const
{
    return QColor::fromRgba(isDark(palette) ? dark : light);
}

//____________________________________________________________________
Finder::ButtonState &Finder::buttonState(const QWidget *button) const
{
    auto it = _buttons.find(button);
    if (it != _buttons.end()) {
        return it.value();
    }

    ButtonState state;
    auto self = const_cast<Finder *>(this);
    QPointer<QWidget> target(const_cast<QWidget *>(button));
    state.hover = new QVariantAnimation(self);
    state.hover->setStartValue(0.0);
    state.hover->setEndValue(0.0);
    state.press = new QVariantAnimation(self);
    state.press->setStartValue(1.0);
    state.press->setEndValue(1.0);
    for (QVariantAnimation *animation : {state.hover, state.press}) {
        connect(animation, &QVariantAnimation::valueChanged, self, [target]() {
            if (target) {
                target->update();
            }
        });
    }
    connect(button, &QObject::destroyed, self, [self](QObject *object) {
        auto state = self->_buttons.take(object);
        delete state.hover;
        delete state.press;
    });
    return _buttons.insert(button, state).value();
}

//____________________________________________________________________
QRectF Finder::pillRect(const Group &group, const QToolButton *button) const
{
    const qreal inset = Tokens::FinderSelectedInset;
    QRectF rect(button->geometry());
    rect.setTop(group.rect.top());
    rect.setHeight(group.rect.height());
    return rect.adjusted(inset, inset, -inset, -inset);
}

//____________________________________________________________________
Finder::Pill &Finder::pillFor(const Group &group) const
{
    QToolButton *first = group.buttons.first();
    const QObject *key = first;
    if (QAction *action = first->defaultAction(); action && action->actionGroup()) {
        key = action->actionGroup();
    }

    auto it = _pills.find(key);
    if (it == _pills.end()) {
        Pill pill;
        auto self = const_cast<Finder *>(this);
        pill.slide = new QVariantAnimation(self);
        pill.slide->setStartValue(1.0);
        pill.slide->setEndValue(1.0);
        connect(pill.slide, &QVariantAnimation::valueChanged, self, [self, key]() {
            const auto pill = self->_pills.value(key);
            for (const auto &button : pill.buttons) {
                if (button) {
                    button->update();
                }
            }
        });
        connect(key, &QObject::destroyed, self, [self](QObject *object) {
            delete self->_pills.take(object).slide;
        });
        it = _pills.insert(key, pill);
    }

    Pill &pill = it.value();
    pill.buttons.clear();
    QToolButton *checked = nullptr;
    for (QToolButton *button : group.buttons) {
        pill.buttons.append(button);
        if (!checked && button->isChecked()) {
            checked = button;
        }
    }

    const QRectF target = checked ? pillRect(group, checked) : QRectF();
    const qreal progress = pill.slide->currentValue().toReal();
    const QRectF shown = lerp(pill.from, pill.to, progress);
    if (checked != pill.current) {
        // slide from where the pill is now to the new button
        const bool animate = pill.current && checked && shown.isValid();
        pill.from = animate ? shown : target;
        pill.to = target;
        pill.current = checked;
        if (animate) {
            pill.slide->stop();
            pill.slide->setStartValue(0.0);
            pill.slide->setEndValue(1.0);
            pill.slide->setDuration(Tokens::FinderSlideMs);
            QEasingCurve curve(QEasingCurve::OutBack);
            curve.setOvershoot(Tokens::FinderSlideOvershoot);
            pill.slide->setEasingCurve(curve);
            pill.slide->start();
        } else {
            pill.slide->stop();
            pill.slide->setStartValue(1.0);
            pill.slide->setEndValue(1.0);
        }
    } else if (pill.slide->state() != QAbstractAnimation::Running) {
        // relayout (window resized): follow the button
        pill.from = target;
        pill.to = target;
    } else {
        pill.to = target;
    }
    return pill;
}

//____________________________________________________________________
bool Finder::drawToolButton(const QStyleOptionToolButton *option, QPainter *painter, const QWidget *widget) const
{
    if (!isFinderToolButton(widget)) {
        return false;
    }
    auto button = static_cast<const QToolButton *>(widget);
    if (button->width() <= 0) {
        // the magnifier while the search field is shown
        return true;
    }
    const Group group = groupFor(button);
    if (group.buttons.isEmpty()) {
        return false;
    }

    const QPalette &palette(option->palette);
    const QStyle::State &state(option->state);
    const bool enabled(state & QStyle::State_Enabled);
    const bool hovered(enabled && (state & QStyle::State_MouseOver));
    const bool pressed(enabled && (state & QStyle::State_Sunken));
    const bool checked(state & QStyle::State_On);
    const bool single(group.buttons.size() == 1);
    const QString name(actionName(button));
    const bool hamburger(name == QLatin1String("hamburger_menu"));
    const bool hasMenu(showsMenuArrow(option) && !hamburger);

    // Liquid Glass feedback: hover fades in, a press gives way and the release
    // springs back
    ButtonState &buttonState(this->buttonState(widget));
    if (hovered != buttonState.hovered) {
        buttonState.hovered = hovered;
        animateTo(buttonState.hover, hovered ? 1.0 : 0.0, Tokens::FinderHoverMs, QEasingCurve::OutCubic);
    }
    if (pressed != buttonState.pressed) {
        buttonState.pressed = pressed;
        if (pressed) {
            animateTo(buttonState.press, Tokens::FinderPressScale, Tokens::FinderPressMs, QEasingCurve::OutCubic);
        } else {
            animateTo(buttonState.press, 1.0, Tokens::FinderReleaseMs, springCurve());
        }
    }
    const qreal hover = buttonState.hover->currentValue().toReal();
    const qreal scale = buttonState.press->currentValue().toReal();
    const qreal pressAmount = qBound(0.0, (1.0 - scale) / (1.0 - Tokens::FinderPressScale), 1.0);

    painter->save();
    painter->setRenderHint(QPainter::Antialiasing);
    painter->setRenderHint(QPainter::SmoothPixmapTransform);

    // draw in toolbar coordinates: every button paints the whole capsule of its
    // group, clipped to itself, so the capsule looks continuous
    painter->translate(-button->pos());
    painter->setClipRect(button->geometry(), Qt::IntersectClip);

    const QRectF capsule = QRectF(group.rect).adjusted(0.5, 0.5, -0.5, -0.5);
    const qreal radius = capsule.height() / 2;

    if (single && scale != 1.0) {
        const QPointF center = capsule.center();
        painter->translate(center);
        painter->scale(scale, scale);
        painter->translate(-center);
    }

    // capsule
    painter->setPen(QPen(token(Tokens::FinderCapsuleBorderLight, Tokens::FinderCapsuleBorderDark, palette), 1));
    painter->setBrush(token(Tokens::FinderCapsuleLight, Tokens::FinderCapsuleDark, palette));
    painter->drawRoundedRect(capsule, radius, radius);
    painter->setPen(Qt::NoPen);

    // dividers between ‹ › and between the unselected segments
    if (!single && (group.navigation || group.segmented)) {
        painter->setPen(QPen(_helper.separatorColor(palette), 1));
        for (int i = 1; i < group.buttons.size(); ++i) {
            const QToolButton *left = group.buttons.at(i - 1);
            const QToolButton *right = group.buttons.at(i);
            if (group.segmented && (left->isChecked() || right->isChecked())) {
                continue;
            }
            const qreal x = right->geometry().left();
            const qreal half = Tokens::FinderDividerHeight / 2.0;
            painter->drawLine(QPointF(x, capsule.center().y() - half), QPointF(x, capsule.center().y() + half));
        }
        painter->setPen(Qt::NoPen);
    }

    // pill of the segmented control (slides to the selected button)
    const QColor selectedColor(token(Tokens::FinderSelectedLight, Tokens::FinderSelectedDark, palette));
    if (group.segmented) {
        const Pill &pill = pillFor(group);
        const QRectF rect = lerp(pill.from, pill.to, pill.slide->currentValue().toReal());
        if (rect.isValid()) {
            painter->setBrush(selectedColor);
            painter->drawRoundedRect(rect, rect.height() / 2, rect.height() / 2);
        }
    }

    // segment of this button
    const qreal inset = Tokens::FinderSelectedInset;
    QRectF segment = single ? capsule : QRectF(button->geometry()).intersected(capsule);
    segment.setTop(capsule.top());
    segment.setHeight(capsule.height());
    segment.adjust(inset, inset, -inset, -inset);
    const qreal segmentRadius = segment.height() / 2;

    if (!single && scale != 1.0) {
        const QPointF center = segment.center();
        painter->translate(center);
        painter->scale(scale, scale);
        painter->translate(-center);
    }

    if (checked && !group.segmented) {
        painter->setBrush(selectedColor);
        painter->drawRoundedRect(segment, segmentRadius, segmentRadius);
    }
    if (hover > 0 || pressAmount > 0) {
        QColor highlight(token(Tokens::FinderHoverLight, Tokens::FinderHoverDark, palette));
        highlight.setAlphaF(highlight.alphaF() * qMin(1.0, hover + pressAmount) * (1.0 + pressAmount));
        painter->setBrush(highlight);
        painter->drawRoundedRect(segment, segmentRadius, segmentRadius);
    }

    // contents: glyph (or text) and the ⌄ of menus
    QRectF content(button->geometry());
    content.setTop(capsule.top());
    content.setHeight(capsule.height());
    QRectF arrow;
    if (hasMenu) {
        arrow = content;
        arrow.setLeft(content.right() - Tokens::FinderMenuArrow - inset - 2);
        arrow.setRight(content.right() - inset - 2);
        content.setRight(arrow.left() + 2);
    }

    QColor foreground(palette.color(enabled ? QPalette::Active : QPalette::Disabled, QPalette::WindowText));
    if (name == QLatin1String("toggle_search")) {
        // Finder's magnifier
        QPen pen(foreground, Tokens::FinderGlyphSearchStroke);
        pen.setCapStyle(Qt::RoundCap);
        painter->setPen(pen);
        painter->setBrush(Qt::NoBrush);
        const QPointF c = content.center() + QPointF(Tokens::FinderGlyphSearchOffset, Tokens::FinderGlyphSearchOffset);
        const qreal r = Tokens::FinderGlyphSearchRadius;
        painter->drawEllipse(c, r, r);
        const qreal d = r * 0.7071;
        const qreal start = Tokens::FinderGlyphSearchHandleStart;
        const qreal end = Tokens::FinderGlyphSearchHandleEnd;
        painter->drawLine(QPointF(c.x() + d + start, c.y() + d + start), QPointF(c.x() + d + end, c.y() + d + end));

    } else if (name == QLatin1String("group_by")) {
        // Finder's group glyph: two rows of three rounded squares
        painter->setPen(QPen(foreground, Tokens::FinderGlyphGroupStroke));
        painter->setBrush(Qt::NoBrush);
        const qreal cell = Tokens::FinderGlyphGroupCell;
        const qreal gap = Tokens::FinderGlyphGroupGap;
        const QPointF origin(content.center().x() - (3 * cell + 2 * gap) / 2, content.center().y() - (2 * cell + gap) / 2);
        for (int row = 0; row < 2; ++row) {
            for (int column = 0; column < 3; ++column) {
                painter->drawRoundedRect(QRectF(origin.x() + column * (cell + gap), origin.y() + row * (cell + gap), cell, cell),
                                         Tokens::FinderGlyphGroupRadius, Tokens::FinderGlyphGroupRadius);
            }
        }

    } else if (hamburger) {
        // Finder's «⋯»
        painter->setBrush(foreground);
        const qreal dot = Tokens::FinderGlyphMoreDot;
        const qreal step = Tokens::FinderGlyphMoreStep;
        const QPointF center = content.center();
        for (int i = -1; i <= 1; ++i) {
            painter->drawEllipse(QPointF(center.x() + i * step, center.y()), dot / 2, dot / 2);
        }

    } else if (!option->icon.isNull()) {
        const int size = Tokens::FinderIconSize;
        const qreal dpr = painter->device() ? painter->device()->devicePixelRatioF() : qApp->devicePixelRatio();
        const QIcon::Mode mode = enabled ? QIcon::Normal : QIcon::Disabled;
        const QIcon::State iconState = checked ? QIcon::On : QIcon::Off;
        const QPixmap pixmap = option->icon.pixmap(QSize(size, size), dpr, mode, iconState);
        const QSizeF pixmapSize = QSizeF(pixmap.size()) / pixmap.devicePixelRatio();
        const QPointF topLeft(content.center().x() - pixmapSize.width() / 2, content.center().y() - pixmapSize.height() / 2);
        painter->drawPixmap(QPointF(qRound(topLeft.x()), qRound(topLeft.y())), pixmap);

    } else {
        painter->setPen(foreground);
        painter->setFont(option->font);
        painter->drawText(content, Qt::AlignCenter, option->text);
    }

    if (hasMenu) {
        // chevron ⌄
        QPen pen(foreground, Tokens::FinderGlyphMenuChevronStroke);
        pen.setCapStyle(Qt::RoundCap);
        pen.setJoinStyle(Qt::RoundJoin);
        painter->setPen(pen);
        painter->setBrush(Qt::NoBrush);
        const QPointF c = arrow.center();
        const qreal w = Tokens::FinderGlyphMenuChevronWidth;
        const qreal h = Tokens::FinderGlyphMenuChevronHeight;
        painter->drawPolyline(QPolygonF({QPointF(c.x() - w, c.y() - h), QPointF(c.x(), c.y() + h), QPointF(c.x() + w, c.y() - h)}));
    }

    painter->restore();
    return true;
}

//____________________________________________________________________
QColor Finder::sidebarBackground(const QWidget *widget, const QPalette &palette, bool *clear) const
{
    // same as the sidebar (Style::eventFilterDockWidget): the first row and
    // the sidebar read as one surface
    QColor color = _helper.sidebarColor(palette);
    *clear = widget && _isTranslucent && _isTranslucent(widget->window());
    if (*clear) {
        color.setAlphaF(StyleConfigData::dolphinSidebarOpacity() / 100.0);
    }
    return color;
}

//____________________________________________________________________
bool Finder::drawToolBarBackground(const QStyleOption *option, QPainter *painter, const QWidget *widget) const
{
    if (!isFinderToolBar(widget)) {
        return false;
    }

    painter->save();
    painter->setRenderHint(QPainter::Antialiasing, false);
    bool clear = false;
    const QColor background = sidebarBackground(widget, option->palette, &clear);
    if (clear) {
        _helper.renderTransparentArea(painter, option->rect);
    }
    painter->fillRect(option->rect, background);
    painter->restore();

    if (isIntegratedWindow(widget->window())) {
        renderLights(painter, widget);
    }
    return true;
}

//____________________________________________________________________
bool Finder::drawDockSeparator(const QStyleOption *option, QPainter *painter, const QWidget *widget) const
{
    // the sidebar meets the content without a gap
    if (!_active || !qobject_cast<const QMainWindow *>(widget)) {
        return false;
    }
    bool clear = false;
    const QColor background = sidebarBackground(widget, option->palette, &clear);
    painter->save();
    if (clear) {
        _helper.renderTransparentArea(painter, option->rect);
    }
    painter->fillRect(option->rect, background);
    painter->restore();
    return true;
}

//____________________________________________________________________
void Finder::updateSearch(QWidget *bar) const
{
    auto mainWindow = qobject_cast<QMainWindow *>(bar->window());
    QToolBar *toolBar = mainWindow ? mainWindow->findChild<QToolBar *>(QStringLiteral("mainToolBar"), Qt::FindDirectChildrenOnly) : nullptr;
    if (!toolBar || !isFinderToolBar(toolBar)) {
        return;
    }

    // the field is the line edit next to the "Here" / "Everywhere" buttons
    auto editor = qobject_cast<QLineEdit *>(bar->property("_goldenglass_searchEditor").value<QObject *>());
    if (!editor) {
        const auto edits = bar->findChildren<QLineEdit *>();
        for (QLineEdit *edit : edits) {
            if (!edit->isClearButtonEnabled() || !edit->parentWidget()) {
                continue;
            }
            const auto buttons = edit->parentWidget()->findChildren<QToolButton *>(Qt::FindDirectChildrenOnly);
            if (std::any_of(buttons.cbegin(), buttons.cend(), [](const QToolButton *button) {
                    return button->isCheckable();
                })) {
                editor = edit;
                break;
            }
        }
        if (!editor) {
            return;
        }
        bar->setProperty("_goldenglass_searchEditor", QVariant::fromValue<QObject *>(editor));
    }

    if (!bar->property("_goldenglass_searchLayout").toBool()) {
        // the bar keeps one row: Here / Everywhere and Filter; Esc closes it
        QWidget *contents = editor->parentWidget();
        auto top = contents ? qobject_cast<QBoxLayout *>(contents->layout()) : nullptr;
        if (!top || top->count() < 2) {
            return;
        }
        auto firstRow = qobject_cast<QBoxLayout *>(top->itemAt(0)->layout());
        QLayout *secondRow = top->itemAt(1)->layout();
        if (!firstRow || !secondRow) {
            return;
        }
        const auto buttons = contents->findChildren<QToolButton *>(Qt::FindDirectChildrenOnly);
        for (QToolButton *button : buttons) {
            if (firstRow->indexOf(button) < 0) {
                continue;
            }
            if (button->menu()) {
                firstRow->removeWidget(button);
                secondRow->addWidget(button);
            } else if (!button->isHidden()) {
                button->setProperty("_goldenglass_searchHidden", true);
                button->hide();
            }
        }

        // Dolphin's field stays in its bar (the bar keeps using it), shrunk to
        // nothing: the field in the toolbar mirrors it and takes its focus
        editor->setMaximumSize(0, 0);
        editor->setProperty("_goldenglass_searchSource", true);
        editor->setProperty("_goldenglass_searchBar", QVariant::fromValue<QObject *>(bar));
        editor->installEventFilter(const_cast<Finder *>(this));
        bar->setProperty("_goldenglass_searchLayout", true);
        _searchBars.append(bar);
    }

    // the field in the toolbar, where the magnifier is; it belongs to the
    // toolbar, so it is created again if XMLGUI rebuilds the toolbar
    QLineEdit *field = _searchFields.value(bar);
    if (!field || field->parentWidget() != toolBar) {
        delete field;
        field = new QLineEdit;
        field->setProperty("_goldenglass_finderSearch", true);
        field->setProperty("_goldenglass_searchBar", QVariant::fromValue<QObject *>(bar));
        field->setClearButtonEnabled(true);
        // fixed: sharing the free space with the title would make them resize
        // each other in a loop
        field->setFixedSize(Tokens::FinderSearchWidth, Tokens::FinderCapsuleHeight);
        field->setTextMargins(Tokens::FinderCapsuleHeight * 2 / 3, 0, 2, 0);
        field->setPlaceholderText(editor->placeholderText());
        field->setText(editor->text());
        field->installEventFilter(const_cast<Finder *>(this));

        // what the user types reaches the bar as if typed in its own field
        QPointer<QLineEdit> source(editor);
        connect(field, &QLineEdit::textEdited, field, [source](const QString &text) {
            if (source) {
                source->setText(text);
                Q_EMIT source->textEdited(text);
            }
        });
        connect(field, &QLineEdit::returnPressed, field, [source]() {
            if (source) {
                Q_EMIT source->returnPressed();
            }
        });
        connect(editor, &QLineEdit::textChanged, field, [field, source](const QString &text) {
            if (field->text() != text) {
                field->setText(text);
            }
            if (source) {
                field->setPlaceholderText(source->placeholderText());
            }
        });

        QAction *before = nullptr;
        const auto actions = toolBar->actions();
        for (QAction *candidate : actions) {
            if (candidate->objectName() == QLatin1String("toggle_search")) {
                before = candidate;
                break;
            }
        }
        QPointer<QAction> action(toolBar->insertWidget(before, field));
        _searchFields.insert(bar, field);
        if (!bar->property("_goldenglass_searchCleanup").toBool()) {
            bar->setProperty("_goldenglass_searchCleanup", true);
            // the field goes with its tab
            auto self = const_cast<Finder *>(this);
            connect(bar, &QObject::destroyed, self, [self](QObject *object) {
                if (QLineEdit *field = self->_searchFields.take(object)) {
                    QToolBar *toolBar = qobject_cast<QToolBar *>(field->parentWidget());
                    const auto actions = toolBar ? toolBar->actions() : QList<QAction *>();
                    for (QAction *action : actions) {
                        if (toolBar->widgetForAction(action) == field) {
                            delete action; // deletes the field too
                            break;
                        }
                    }
                }
                self->_searchBars.removeAll(nullptr);
            });
        }
    }

    QAction *action = nullptr;
    const auto toolBarActions = toolBar->actions();
    for (QAction *candidate : toolBarActions) {
        if (toolBar->widgetForAction(candidate) == field) {
            action = candidate;
            break;
        }
    }
    if (!action) {
        return;
    }

    // shown while its bar is searching in a visible tab
    const bool searching = bar->isEnabled() && bar->isVisible();
    if (action->isVisible() != searching) {
        if (!searching && field->hasFocus()) {
            // as the bar does when its own field loses the search
            QMetaObject::invokeMethod(bar, "focusViewRequest");
        }
        action->setVisible(searching);
    }

    bool shown = false;
    const auto actions = toolBar->actions();
    for (QAction *candidate : actions) {
        QWidget *widget = toolBar->widgetForAction(candidate);
        shown = shown || (candidate->isVisible() && widget && widget->property("_goldenglass_finderSearch").toBool());
    }
    if (toolBar->property("_goldenglass_searchShown").toBool() != shown) {
        toolBar->setProperty("_goldenglass_searchShown", shown);
        for (QAction *candidate : actions) {
            if (candidate->objectName() == QLatin1String("toggle_search")) {
                if (QWidget *magnifier = toolBar->widgetForAction(candidate)) {
                    magnifier->updateGeometry();
                    magnifier->update();
                }
            }
        }
    }
}

//____________________________________________________________________
bool Finder::drawSearchField(const QStyleOption *option, QPainter *painter, const QWidget *widget, bool frame) const
{
    if (!widget || !widget->property("_goldenglass_finderSearch").toBool()) {
        return false;
    }
    if (frame) {
        // all drawn with the panel
        return true;
    }

    // capsule as the toolbar buttons, magnifier inside, macOS focus ring
    const QPalette &palette(option->palette);
    const bool focus = (option->state & QStyle::State_HasFocus) || widget->hasFocus();
    const qreal ring = Tokens::FocusRingWidth;
    const QRectF body = QRectF(widget->rect()).adjusted(ring - 0.5, ring - 0.5, -ring + 0.5, -ring + 0.5);
    const qreal radius = body.height() / 2;

    painter->save();
    painter->setRenderHint(QPainter::Antialiasing);
    painter->setPen(QPen(token(Tokens::FinderCapsuleBorderLight, Tokens::FinderCapsuleBorderDark, palette), 1));
    painter->setBrush(token(Tokens::FinderCapsuleLight, Tokens::FinderCapsuleDark, palette));
    painter->drawRoundedRect(body, radius, radius);

    if (focus) {
        QColor accent(palette.color(QPalette::Active, QPalette::Highlight));
        accent.setAlphaF(Tokens::FocusRingAlpha);
        painter->setPen(QPen(accent, ring));
        painter->setBrush(Qt::NoBrush);
        const QRectF ringRect = body.adjusted(-ring / 2 + 0.5, -ring / 2 + 0.5, ring / 2 - 0.5, ring / 2 - 0.5);
        painter->drawRoundedRect(ringRect, ringRect.height() / 2, ringRect.height() / 2);
    }

    // magnifier, in the placeholder color
    QColor glyph(palette.color(QPalette::Text));
    glyph.setAlphaF(glyph.alphaF() * Tokens::FinderGlyphFieldSearchAlpha);
    QPen pen(glyph, Tokens::FinderGlyphFieldSearchStroke);
    pen.setCapStyle(Qt::RoundCap);
    painter->setPen(pen);
    painter->setBrush(Qt::NoBrush);
    const qreal r = Tokens::FinderGlyphFieldSearchRadius;
    const QPointF c(body.left() + body.height() / 2 + Tokens::FinderGlyphFieldSearchOffset,
                    body.center().y() - Tokens::FinderGlyphFieldSearchOffset);
    painter->drawEllipse(c, r, r);
    const qreal d = r * 0.7071;
    const qreal start = Tokens::FinderGlyphFieldSearchHandleStart;
    const qreal end = Tokens::FinderGlyphFieldSearchHandleEnd;
    painter->drawLine(QPointF(c.x() + d + start, c.y() + d + start), QPointF(c.x() + d + end, c.y() + d + end));
    painter->restore();
    return true;
}

//____________________________________________________________________
QPointF Finder::lightCenter(const QWidget *toolBar, Light light) const
{
    // Apple's rule: the first light is as far from the left edge as from the top
    const qreal padding = toolBar->height() / 2.0;
    const qreal step = Tokens::TrafficLightDiameter + Tokens::TrafficLightGap;
    return QPointF(padding + int(light) * step, toolBar->height() / 2.0);
}

//____________________________________________________________________
QRectF Finder::lightsRect(const QWidget *toolBar) const
{
    const qreal r = Tokens::TrafficLightDiameter / 2.0;
    const QPointF first = lightCenter(toolBar, Light::Close);
    const QPointF last = lightCenter(toolBar, Light::Zoom);
    const qreal margin = Tokens::FinderGlyphLightHitMargin;
    return QRectF(QPointF(first.x() - r, first.y() - r), QPointF(last.x() + r, last.y() + r)).adjusted(-margin, -margin, margin, margin);
}

//____________________________________________________________________
Finder::Light Finder::lightAt(const QWidget *toolBar, const QPointF &position) const
{
    const qreal r = Tokens::TrafficLightDiameter / 2.0 + Tokens::FinderGlyphLightHitSlop;
    for (const Light light : {Light::Close, Light::Minimize, Light::Zoom}) {
        const QPointF delta = position - lightCenter(toolBar, light);
        if (QPointF::dotProduct(delta, delta) <= r * r) {
            return light;
        }
    }
    return Light::None;
}

//____________________________________________________________________
void Finder::renderLights(QPainter *painter, const QWidget *toolBar) const
{
    const Lights lights = _lights.value(toolBar);
    const QWidget *window = toolBar->window();

    TrafficLight::State state;
    state.lit = window->isActiveWindow() || Tokens::TrafficLightInactiveColored || lights.hovered;
    state.maximized = window->isMaximized();
    state.darkTitleBar = isDark(toolBar->palette());
    state.glyphOpacity = lights.glyphs ? lights.glyphs->currentValue().toReal() : 0.0;

    painter->save();
    painter->setRenderHint(QPainter::Antialiasing);
    const TrafficLight::Kind kinds[] = {TrafficLight::Kind::Close, TrafficLight::Kind::Minimize, TrafficLight::Kind::Zoom};
    for (const Light light : {Light::Close, Light::Minimize, Light::Zoom}) {
        state.pressed = lights.pressed == light;
        TrafficLight::render(painter, lightCenter(toolBar, light), kinds[int(light)], state);
    }
    painter->restore();
}

//____________________________________________________________________
void Finder::triggerLight(QWidget *window, Light light) const
{
    QPointer<QWidget> target(window);
    // after the release has been delivered
    QTimer::singleShot(0, window, [target, light]() {
        if (!target) {
            return;
        }
        switch (light) {
        case Light::Close:
            target->close();
            break;
        case Light::Minimize:
            target->showMinimized();
            break;
        case Light::Zoom:
            if (target->isMaximized()) {
                target->showNormal();
            } else {
                target->showMaximized();
            }
            break;
        case Light::None:
            break;
        }
    });
}

//____________________________________________________________________
void Finder::updateToolBarMargins(QWidget *window) const
{
    auto mainWindow = qobject_cast<QMainWindow *>(window);
    if (!mainWindow) {
        return;
    }
    auto toolBar = mainWindow->findChild<QToolBar *>(QStringLiteral("mainToolBar"), Qt::FindDirectChildrenOnly);
    if (!toolBar || !isFinderToolBar(toolBar)) {
        return;
    }

    // QToolBar adds its own margin before the first button
    const int itemMargin = toolBarItemMargin() + 2;
    int left = 0;
    if (isIntegratedWindow(mainWindow)) {
        const qreal lightsRight = lightCenter(toolBar, Light::Zoom).x() + Tokens::TrafficLightDiameter / 2.0;
        left = qCeil(lightsRight) + Tokens::FinderCapsuleGap;
    }

    // the buttons start where the sidebar ends, as in Finder
    const auto docks = mainWindow->findChildren<QDockWidget *>(Qt::FindDirectChildrenOnly);
    for (const QDockWidget *dock : docks) {
        if (dock->isVisible() && !dock->isFloating() && mainWindow->dockWidgetArea(const_cast<QDockWidget *>(dock)) == Qt::LeftDockWidgetArea) {
            left = qMax(left, dock->geometry().right() + 1);
        }
    }

    // QToolBarLayout only works with equal margins (it swaps left and top), so
    // they center the capsules in the row and a spacer in front holds the
    // sidebar column. QToolBar resets them on style changes (see the filter).
    if (QLayout *layout = toolBar->layout()) {
        const QMargins margins(itemMargin, itemMargin, itemMargin, itemMargin);
        if (layout->contentsMargins() != margins) {
            layout->setContentsMargins(margins);
        }
    }
    if (QWidget *spacer = ensureLeadSpacer(toolBar)) {
        const int width = left > 0 ? qMax(0, left + Tokens::FinderCapsuleGap - itemMargin) : 0;
        if (spacer->width() != width || spacer->minimumWidth() != width) {
            spacer->setFixedWidth(width);
        }
    }
}

//____________________________________________________________________
QWidget *Finder::ensureLeadSpacer(QToolBar *toolBar) const
{
    static const QString name = QStringLiteral("goldenglass_finder_lead");
    if (_updatingSpacer) {
        return nullptr;
    }
    _updatingSpacer = true;

    auto spacer = toolBar->findChild<QWidget *>(name, Qt::FindDirectChildrenOnly);
    QAction *spacerAction = nullptr;
    const auto actions = toolBar->actions();
    if (spacer) {
        for (QAction *action : actions) {
            if (toolBar->widgetForAction(action) == spacer) {
                spacerAction = action;
                break;
            }
        }
    }

    if (!spacer || !spacerAction) {
        // XMLGUI rebuilt the toolbar: a new spacer in front
        delete spacer;
        spacer = new QWidget(toolBar);
        spacer->setObjectName(name);
        spacer->setAttribute(Qt::WA_TransparentForMouseEvents);
        spacer->setFixedSize(0, 1);
        toolBar->insertWidget(actions.value(0), spacer);
    } else if (actions.first() != spacerAction) {
        toolBar->removeAction(spacerAction);
        toolBar->insertAction(toolBar->actions().value(0), spacerAction);
    }

    _updatingSpacer = false;
    return spacer;
}

//____________________________________________________________________
void Finder::updateNavigator(QWidget *navigator) const
{
    if (_updatingNavigator || !isFinderNavigator(navigator)) {
        return;
    }
    _updatingNavigator = true;

    // the folder name is the window title
    if (!navigator->property("_goldenglass_finderTitle").toBool()) {
        navigator->setProperty("_goldenglass_finderTitle", true);
        navigator->setProperty("_goldenglass_finderFont", navigator->testAttribute(Qt::WA_SetFont) ? QVariant(navigator->font()) : QVariant());
        QFont font(navigator->font());
        font.setPointSizeF(QApplication::font().pointSizeF() * Tokens::FinderTitleScale);
        navigator->setFont(font);
    }

    // the buttons follow the path; the last one is the current folder (KIO
    // deletes the ones past it). Everything else hides: Finder only shows the
    // folder name. Ctrl+L still edits the location.
    const auto children = navigator->children();
    QWidget *current = nullptr;
    bool editable = false;
    for (QObject *child : children) {
        if (isKioPrivate(child, "KUrlNavigatorButton")) {
            current = static_cast<QWidget *>(child);
        } else if (child->inherits("KUrlComboBox")) {
            // editing the location (Ctrl+L): KIO hides the breadcrumb itself
            editable = !static_cast<QWidget *>(child)->isHidden();
        }
    }
    for (QObject *child : children) {
        if (!child->isWidgetType()) {
            continue;
        }
        auto widget = static_cast<QWidget *>(child);
        if (widget == current) {
            if (widget->isHidden() && !editable) {
                widget->show();
            }
        } else if (isKioPrivate(child, "KUrlNavigatorButton") || isKioPrivate(child, "KUrlNavigatorDropDownButton")
                   || isKioPrivate(child, "KUrlNavigatorPlacesSelector")) {
            if (!widget->isHidden()) {
                widget->setProperty("_goldenglass_finderHidden", true);
                widget->hide();
            }
        } else if (isKioPrivate(child, "KUrlNavigatorToggleButton")) {
            // the empty space drags the window instead of editing the path
            if (!widget->testAttribute(Qt::WA_TransparentForMouseEvents)) {
                widget->setProperty("_goldenglass_finderTransparent", true);
                widget->setAttribute(Qt::WA_TransparentForMouseEvents);
            }
        }
    }

    _updatingNavigator = false;
}

//____________________________________________________________________
bool Finder::drawNavigatorButton(const QWidget *widget) const
{
    // the folder title has no hover background
    if (!widget || !isKioPrivate(widget, "KUrlNavigatorButtonBase")) {
        return false;
    }
    return isFinderNavigator(widget->parentWidget());
}

//____________________________________________________________________
bool Finder::eventFilter(QObject *object, QEvent *event)
{
    if (auto toolBar = qobject_cast<QToolBar *>(object)) {
        return eventFilterToolBar(toolBar, event);
    }

    if (auto dock = qobject_cast<QDockWidget *>(object)) {
        switch (event->type()) {
        case QEvent::Resize:
        case QEvent::Move:
        case QEvent::Show:
        case QEvent::Hide:
            updateToolBarMargins(dock->window());
            break;
        default:
            break;
        }
        return false;
    }

    if (!object->isWidgetType()) {
        return false;
    }
    auto widget = static_cast<QWidget *>(object);

    if (widget->inherits("Search::Bar")) {
        switch (event->type()) {
        case QEvent::Paint: {
            // the scope row continues the toolbar surface, like the header
            QPainter painter(widget);
            bool clear = false;
            const QColor background = sidebarBackground(widget, widget->palette(), &clear);
            if (clear) {
                _helper.renderTransparentArea(&painter, widget->rect());
            }
            painter.fillRect(widget->rect(), background);
            break;
        }
        case QEvent::Show:
        case QEvent::Hide:
        case QEvent::EnabledChange:
            updateSearch(widget);
            break;
        default:
            break;
        }
        return false;
    }

    if (widget->property("_goldenglass_searchSource").toBool()) {
        // Dolphin focuses its own (hidden) field: the toolbar one takes over
        if (event->type() == QEvent::FocusIn) {
            QPointer<QLineEdit> field(_searchFields.value(widget->property("_goldenglass_searchBar").value<QObject *>()));
            QTimer::singleShot(0, this, [field]() {
                if (field && field->isVisible()) {
                    field->setFocus(Qt::OtherFocusReason);
                    field->selectAll();
                }
            });
        }
        return false;
    }

    if (widget->property("_goldenglass_finderSearch").toBool()) {
        // the toolbar field: Esc (clear, then close) and ↓ (to the view) go to
        // the bar, as from its own field
        auto bar = qobject_cast<QWidget *>(widget->property("_goldenglass_searchBar").value<QObject *>());
        auto keyEvent = static_cast<QKeyEvent *>(event);
        if (bar && event->type() == QEvent::KeyPress && keyEvent->key() == Qt::Key_Escape) {
            QKeyEvent copy(QEvent::KeyPress, keyEvent->key(), keyEvent->modifiers(), keyEvent->text());
            QCoreApplication::sendEvent(bar, &copy);
            return true;
        }
        if (bar && event->type() == QEvent::KeyRelease && keyEvent->key() == Qt::Key_Down) {
            QKeyEvent copy(QEvent::KeyRelease, keyEvent->key(), keyEvent->modifiers(), keyEvent->text());
            QCoreApplication::sendEvent(bar, &copy);
            return true;
        }
        return false;
    }

    if (widget->inherits("KUrlNavigator")) {
        if (event->type() == QEvent::LayoutRequest || event->type() == QEvent::Resize || event->type() == QEvent::Show
            || event->type() == QEvent::ParentChange) {
            // queued: KIO hides the buttons past the new folder and deletes
            // them later; by then they are gone and the last one is current
            if (!widget->property("_goldenglass_finderPending").toBool()) {
                widget->setProperty("_goldenglass_finderPending", true);
                QPointer<QWidget> navigator(widget);
                QMetaObject::invokeMethod(
                    this,
                    [this, navigator]() {
                        if (navigator) {
                            navigator->setProperty("_goldenglass_finderPending", false);
                            updateNavigator(navigator);
                        }
                    },
                    Qt::QueuedConnection);
            }
        }
        return false;
    }

    if (event->type() == QEvent::Paint) {
        if (widget->inherits("KItemListContainer")) {
            auto container = static_cast<QAbstractScrollArea *>(widget);
            // (a translucent view is painted by the style itself)
            if (QWidget *viewport = container->viewport(); viewport && StyleConfigData::dolphinViewOpacity() >= 100) {
                QPainter painter(widget);
                painter.fillRect(widget->rect(), viewport->palette().color(viewport->backgroundRole()));

                // above the view, the toolbar surface continues down to the header
                const QRect top(0, 0, widget->width(), viewport->geometry().top());
                if (top.isValid()) {
                    bool clear = false;
                    const QColor background = sidebarBackground(widget, widget->palette(), &clear);
                    if (clear) {
                        _helper.renderTransparentArea(&painter, top);
                    }
                    painter.fillRect(top, background);
                }
            }
            return false;
        }

        // the sidebar pill lies on the view, under its viewport (it reaches
        // into the viewport margins)
        if (widget->inherits("KFilePlacesView")) {
            paintSidebarSelection(static_cast<QListView *>(widget));
            return false;
        }

        // painted before the view draws its items
        QWidget *parent = widget->parentWidget();
        if (parent && parent->inherits("KFilePlacesView")) {
            // selection, scroll or relayout: the pill follows on the view
            if (syncSidebarSelection(static_cast<QListView *>(parent))) {
                parent->update();
            }
        } else if (parent && parent->inherits("KItemListContainerViewport")) {
            paintStripes(widget);
        }
    }
    return false;
}

//____________________________________________________________________
bool Finder::eventFilterToolBar(QToolBar *toolBar, QEvent *event)
{
    const bool integrated = isIntegratedWindow(toolBar->window());

    // one entry per toolbar, removed with it
    const auto lightsFor = [this, toolBar]() -> Lights & {
        Lights &lights = _lights[toolBar];
        if (!lights.glyphs) {
            lights.glyphs = new QVariantAnimation(this);
            lights.glyphs->setStartValue(0.0);
            lights.glyphs->setEndValue(0.0);
            QPointer<QToolBar> target(toolBar);
            connect(lights.glyphs, &QVariantAnimation::valueChanged, this, [this, target]() {
                if (target) {
                    target->update(lightsRect(target).toAlignedRect());
                }
            });
            connect(toolBar, &QObject::destroyed, this, [this](QObject *object) {
                delete _lights.take(object).glyphs;
            });
        }
        return lights;
    };

    const auto setHovered = [this, toolBar, &lightsFor](bool hovered) {
        Lights &lights = lightsFor();
        if (lights.hovered != hovered) {
            lights.hovered = hovered;
            animateTo(lights.glyphs, hovered ? 1.0 : 0.0, Tokens::FinderHoverMs, QEasingCurve::OutCubic);
            toolBar->update(lightsRect(toolBar).toAlignedRect());
        }
    };

    switch (event->type()) {
    case QEvent::HoverEnter:
    case QEvent::HoverMove:
        if (integrated) {
            setHovered(lightsRect(toolBar).contains(static_cast<QHoverEvent *>(event)->position()));
        }
        break;

    case QEvent::HoverLeave:
        if (integrated) {
            setHovered(false);
        }
        break;

    case QEvent::MouseButtonPress: {
        auto mouseEvent = static_cast<QMouseEvent *>(event);
        if (integrated && mouseEvent->button() == Qt::LeftButton) {
            const Light light = lightAt(toolBar, mouseEvent->position());
            if (light != Light::None) {
                lightsFor().pressed = light;
                toolBar->update(lightsRect(toolBar).toAlignedRect());
                return true;
            }
        }
        break;
    }

    case QEvent::MouseButtonRelease: {
        auto mouseEvent = static_cast<QMouseEvent *>(event);
        auto it = _lights.find(toolBar);
        if (it != _lights.end() && it->pressed != Light::None) {
            const Light pressed = it->pressed;
            it->pressed = Light::None;
            toolBar->update(lightsRect(toolBar).toAlignedRect());
            if (lightAt(toolBar, mouseEvent->position()) == pressed) {
                triggerLight(toolBar->window(), pressed);
            }
            return true;
        }
        break;
    }

    case QEvent::MouseButtonDblClick: {
        // double click on the empty toolbar zooms the window, as in macOS
        auto mouseEvent = static_cast<QMouseEvent *>(event);
        if (integrated && mouseEvent->button() == Qt::LeftButton && !toolBar->childAt(mouseEvent->position().toPoint())) {
            if (lightAt(toolBar, mouseEvent->position()) == Light::None) {
                triggerLight(toolBar->window(), Light::Zoom);
            }
            return true;
        }
        break;
    }

    case QEvent::Show:
    case QEvent::Resize:
        updateToolBarMargins(toolBar->window());
        break;

    case QEvent::ActionAdded:
    case QEvent::ActionRemoved:
    case QEvent::StyleChange: {
        // after QToolBar has reset its layout margins (or XMLGUI its actions,
        // dropping the search fields)
        QPointer<QToolBar> target(toolBar);
        QTimer::singleShot(0, this, [this, target]() {
            if (target) {
                updateToolBarMargins(target->window());
                for (const auto &bar : std::as_const(_searchBars)) {
                    if (bar && bar->window() == target->window()) {
                        updateSearch(bar);
                    }
                }
            }
        });
        break;
    }

    case QEvent::ActivationChange:
    case QEvent::WindowActivate:
    case QEvent::WindowDeactivate:
        toolBar->update(lightsRect(toolBar).toAlignedRect());
        break;

    default:
        break;
    }
    return false;
}

//____________________________________________________________________
bool Finder::drawItemViewItem(const QStyleOptionViewItem *option, QPainter *painter, const QWidget *widget) const
{
    if (!_active) {
        return false;
    }
    const QWidget *view = widget ? widget : option->widget;
    if (!view) {
        return false;
    }

    // sidebar: the selection pill is painted under the items (it slides), and
    // Finder has no hover highlight
    if (view->inherits("KFilePlacesView")) {
        return true;
    }

    // list rows of Dolphin's view: rounded, away from the edges like the stripes
    const QWidget *parent = view->parentWidget();
    if (!parent || !parent->inherits("KItemListContainerViewport")) {
        return false;
    }
    const QStyle::State state(option->state);
    const bool selected(state & QStyle::State_Selected);
    const bool mouseOver(state & QStyle::State_MouseOver);
    if (!selected && !mouseOver) {
        return true;
    }

    // in the details view (it has a header) the selection covers the whole
    // row, disclosure arrow included, inset like the stripes
    QRectF rect(option->rect);
    const QWidget *container = parent->parentWidget();
    if (container && container->property("_goldenglass_finderHeader").toInt() > 0) {
        const qreal x = painter->transform().dx();
        rect.setLeft(Tokens::FinderRowInset - x);
        rect.setRight(view->width() - Tokens::FinderRowInset - x);
    }

    const QPalette &palette(option->palette);
    const bool active(state & QStyle::State_Active);
    QColor color(palette.color(active ? QPalette::Active : QPalette::Inactive, QPalette::Highlight));
    if (!selected) {
        color = token(Tokens::FinderHoverLight, Tokens::FinderHoverDark, palette);
    } else if (!active) {
        // Finder dims the selection of an unfocused list to gray
        color = token(Tokens::FinderSidebarSelectedLight, Tokens::FinderSidebarSelectedDark, palette);
    }

    painter->save();
    painter->setRenderHint(QPainter::Antialiasing);
    painter->setPen(Qt::NoPen);
    painter->setBrush(color);
    painter->drawRoundedRect(rect, Tokens::FinderRowRadius, Tokens::FinderRowRadius);
    painter->restore();
    return true;
}

//____________________________________________________________________
bool Finder::syncSidebarSelection(QListView *view) const
{
    if (!view->selectionModel() || !view->model()) {
        return false;
    }

    QModelIndex index;
    const auto selected = view->selectionModel()->selectedIndexes();
    if (!selected.isEmpty()) {
        index = selected.first();
    }

    auto self = const_cast<Finder *>(this);
    auto it = _sidebars.find(view);
    if (it == _sidebars.end()) {
        SidebarSelection selection;
        selection.slide = new QVariantAnimation(self);
        selection.slide->setStartValue(1.0);
        selection.slide->setEndValue(1.0);
        QPointer<QWidget> target(view);
        connect(selection.slide, &QVariantAnimation::valueChanged, self, [target]() {
            if (target) {
                target->update();
            }
        });
        connect(view, &QObject::destroyed, self, [self](QObject *object) {
            delete self->_sidebars.take(object).slide;
        });
        it = _sidebars.insert(view, selection);
    }
    SidebarSelection &selection = it.value();

    if (!index.isValid()) {
        const bool changed = selection.index.isValid();
        selection.index = QPersistentModelIndex();
        selection.slide->stop();
        return changed;
    }

    // the first place of a section also holds its header: the pill covers the
    // item only (as tall as every place, sidebarItemHeight), across the view
    const QRect itemRect = view->visualRect(index);
    const int rowHeight = qMin(itemRect.height(), int(Tokens::FinderSidebarRowHeight));
    const QPoint offset = view->viewport()->pos();
    const QRectF target(0, offset.y() + itemRect.bottom() + 1 - rowHeight, view->width(), rowHeight);

    if (selection.index != index) {
        const bool animate = selection.index.isValid();
        const qreal progress = selection.slide->currentValue().toReal();
        selection.from = animate ? lerp(selection.from, selection.to, progress) : target;
        selection.to = target;
        selection.index = index;
        selection.slide->stop();
        if (animate) {
            selection.slide->setStartValue(0.0);
            selection.slide->setEndValue(1.0);
            selection.slide->setDuration(Tokens::FinderSidebarSlideMs);
            selection.slide->setEasingCurve(QEasingCurve::OutCubic);
            selection.slide->start();
        } else {
            selection.slide->setStartValue(1.0);
            selection.slide->setEndValue(1.0);
        }
        return true;
    }
    if (selection.to == target) {
        return false;
    }
    // scrolled or resized: follow the item
    selection.to = target;
    if (selection.slide->state() != QAbstractAnimation::Running) {
        selection.from = target;
    }
    return true;
}

//____________________________________________________________________
void Finder::paintSidebarSelection(QListView *view) const
{
    syncSidebarSelection(view);
    const auto it = _sidebars.constFind(view);
    if (it == _sidebars.cend() || !it->index.isValid()) {
        return;
    }

    const QRectF rect = lerp(it->from, it->to, it->slide->currentValue().toReal());
    QPainter painter(view);
    painter.setRenderHint(QPainter::Antialiasing);
    painter.setPen(Qt::NoPen);
    painter.setBrush(token(Tokens::FinderSidebarSelectedLight, Tokens::FinderSidebarSelectedDark, view->palette()));
    const qreal radius = Tokens::FinderSidebarSelectionRadius;
    painter.drawRoundedRect(rect, radius, radius);
}

//____________________________________________________________________
void Finder::paintStripes(QWidget *viewport) const
{
    auto graphicsView = qobject_cast<QGraphicsView *>(viewport->parentWidget());
    if (!graphicsView || !graphicsView->scene()) {
        return;
    }

    // details view only (it has a header); only the items on screen
    QGraphicsObject *listView = nullptr;
    QGraphicsObject *header = nullptr;
    QList<QPair<QRectF, QGraphicsObject *>> rows;
    bool grouped = false;
    const auto items = graphicsView->items(viewport->rect());
    for (QGraphicsItem *item : items) {
        QGraphicsObject *object = item->toGraphicsObject();
        if (!object || !object->isVisible()) {
            continue;
        }
        if (object->inherits("KItemListGroupHeader")) {
            grouped = true;
        } else if (object->inherits("KItemListHeaderWidget")) {
            header = object;
        } else if (object->inherits("KItemListView")) {
            listView = object;
        } else if (object->inherits("KItemListWidget")) {
            rows.append({graphicsView->mapFromScene(object->mapToScene(object->boundingRect())).boundingRect(), object});
        }
    }

    // the header shares the toolbar glass: the blur region follows it
    QWidget *container = graphicsView->parentWidget();
    const QRectF headerRect = header ? graphicsView->mapFromScene(header->mapToScene(header->boundingRect())).boundingRect() : QRectF();
    const int headerHeight = header && listView ? qCeil(headerRect.bottom() + graphicsView->y()) : 0;
    if (container && container->property("_goldenglass_finderHeader").toInt() != headerHeight) {
        container->setProperty("_goldenglass_finderHeader", headerHeight);
        if (_updateBlur) {
            _updateBlur(container->window());
        }
    }

    if (!listView || !header) {
        return;
    }

    QPainter painter(viewport);

    // the toolbar surface reaches the header without a seam
    if (headerRect.top() > 0) {
        const QRect above(0, 0, viewport->width(), qCeil(headerRect.top()));
        bool clear = false;
        const QColor background = sidebarBackground(viewport, viewport->palette(), &clear);
        if (clear) {
            _helper.renderTransparentArea(&painter, above);
        }
        painter.fillRect(above, background);
    }

    // rows keep their height when the folder is empty (Finder still stripes it)
    std::sort(rows.begin(), rows.end(), [](const auto &a, const auto &b) {
        return a.first.top() < b.first.top();
    });
    qreal rowHeight = viewport->property("_goldenglass_rowHeight").toReal();
    if (!rows.isEmpty()) {
        rowHeight = rows.first().first.height();
        viewport->setProperty("_goldenglass_rowHeight", rowHeight);
    }
    if (rowHeight < 4) {
        return;
    }

    const qreal top = headerRect.bottom();
    const qreal inset = Tokens::FinderRowInset;
    const qreal radius = Tokens::FinderRowRadius;
    painter.setRenderHint(QPainter::Antialiasing);
    painter.setPen(Qt::NoPen);
    painter.setBrush(token(Tokens::FinderStripeLight, Tokens::FinderStripeDark, viewport->palette()));
    painter.setClipRect(QRectF(0, top, viewport->width(), viewport->height() - top));
    const auto stripe = [&](qreal y) {
        painter.drawRoundedRect(QRectF(inset, y, viewport->width() - 2 * inset, rowHeight), radius, radius);
    };

    if (const auto alternate = alternateBackgroundFunction(); alternate && !rows.isEmpty()) {
        // Dolphin knows which rows alternate (it restarts in every group)
        for (const auto &row : std::as_const(rows)) {
            if (alternate(row.second)) {
                stripe(row.first.top());
            }
        }
        // past the last row, the alternation goes on to the bottom
        bool striped = alternate(rows.last().second);
        for (qreal y = rows.last().first.bottom(); y < viewport->height(); y += rowHeight) {
            striped = !striped;
            if (striped) {
                stripe(y);
            }
        }
        return;
    }

    // without Dolphin's answer: the odd rows from the first one (not grouped)
    if (grouped) {
        return;
    }
    const qreal scrollOffset = listView->property("scrollOffset").toReal();
    qreal anchorY = top - scrollOffset;
    int anchorIndex = 0;
    if (!rows.isEmpty()) {
        anchorIndex = qRound((rows.first().first.top() - top + scrollOffset) / rowHeight);
        anchorY = rows.first().first.top();
    }
    int index = anchorIndex + qFloor((top - anchorY) / rowHeight);
    for (qreal y = anchorY + (index - anchorIndex) * rowHeight; y < viewport->height(); y += rowHeight, ++index) {
        if (index & 1) {
            stripe(y);
        }
    }
}

//____________________________________________________________________
bool Finder::drawHeader(const QStyleOptionHeader *option, QPainter *painter, const QWidget *widget) const
{
    if (!_active || !widget || !widget->parentWidget() || !widget->parentWidget()->inherits("KItemListContainerViewport")) {
        return false;
    }

    // Finder's column header: on the surface of the toolbar, a hairline below,
    // short separators, the sorted column in bold with its chevron
    const QPalette &palette(option->palette);
    const QRect &rect(option->rect);

    painter->save();
    bool clear = false;
    const QColor background = sidebarBackground(widget, palette, &clear);
    if (clear) {
        painter->setCompositionMode(QPainter::CompositionMode_Source);
    }
    painter->fillRect(rect, background);
    painter->setCompositionMode(QPainter::CompositionMode_SourceOver);

    const QColor separator(_helper.separatorColor(palette));
    painter->fillRect(QRect(rect.left(), rect.bottom(), rect.width(), 1), separator);

    if (option->text.isEmpty()) {
        painter->restore();
        return true;
    }

    // separator on the left of every column but the first
    if (option->section > 0) {
        const int margin = rect.height() / 4;
        painter->fillRect(QRect(rect.left(), rect.top() + margin, 1, rect.height() - 2 * margin), separator);
    }

    const bool sorted = option->sortIndicator != QStyleOptionHeader::None;
    QFont font(painter->font());
    font.setBold(sorted);
    painter->setFont(font);
    QColor text(palette.color(QPalette::WindowText));
    if (!sorted) {
        text.setAlphaF(text.alphaF() * Tokens::FinderGlyphHeaderUnsortedAlpha);
    }
    painter->setPen(text);

    const int padding = Tokens::FinderHeaderPadding;
    const int arrowWidth = sorted ? Tokens::FinderHeaderArrowWidth : 0;
    const QRect textRect = rect.adjusted(padding, 0, -padding - arrowWidth, -1);
    painter->drawText(textRect, Qt::AlignVCenter | Qt::AlignLeft, QFontMetrics(font).elidedText(option->text, Qt::ElideRight, textRect.width()));

    if (sorted) {
        // ascending (Dolphin's SortDown) points up, as in Finder
        const bool up = option->sortIndicator == QStyleOptionHeader::SortDown;
        painter->setRenderHint(QPainter::Antialiasing);
        QPen pen(palette.color(QPalette::WindowText), Tokens::FinderGlyphHeaderChevronStroke);
        pen.setCapStyle(Qt::RoundCap);
        pen.setJoinStyle(Qt::RoundJoin);
        painter->setPen(pen);
        const QPointF c(rect.right() - padding - Tokens::FinderGlyphHeaderChevronInset, rect.center().y() + 0.5);
        const qreal w = Tokens::FinderGlyphHeaderChevronWidth;
        const qreal h = up ? -Tokens::FinderGlyphHeaderChevronHeight : Tokens::FinderGlyphHeaderChevronHeight;
        painter->drawPolyline(QPolygonF({QPointF(c.x() - w, c.y() - h), QPointF(c.x(), c.y() + h), QPointF(c.x() + w, c.y() - h)}));
    }

    painter->restore();
    return true;
}

//____________________________________________________________________
void Finder::applyDolphinDefaults() const
{
    // once per version, and only what the user has not changed yet; solo se
    // marca como hecho si todo se escribió
    KSharedConfig::Ptr styleConfig = KSharedConfig::openConfig(QStringLiteral("goldenglassrc"));
    KConfigGroup finder = styleConfig->group(QStringLiteral("Finder"));
    const bool firstRun = finder.readEntry("DolphinDefaults", 0) < DolphinDefaultsVersion;

    const QString dataDir = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation);
    bool done = true;

    // toolbar: Dolphin's own ui.rc (same version) with Finder's main toolbar.
    // Si Dolphin trae un ui.rc más nuevo, KXMLGUI descarta la copia local y
    // vuelve la barra de Dolphin: la nuestra se escribe de nuevo a partir del
    // nuevo. DolphinUiVersion es la versión del ui.rc ya atendida
    const QString uiFile = dataDir + QStringLiteral("/kxmlgui5/dolphin/dolphinui.rc");
    const bool uiExists = QFile::exists(uiFile);
    QFile shipped(QStringLiteral(":/kxmlgui5/dolphin/dolphinui.rc"));
    if ((uiExists || firstRun) && shipped.open(QIODevice::ReadOnly)) {
        QString xml = QString::fromUtf8(shipped.readAll());
        const int shippedVersion = uiRcVersion(xml);
        if (!uiExists || finder.readEntry("DolphinUiVersion", -1) != shippedVersion) {
            QString previous;
            bool write = !uiExists;
            if (uiExists) {
                QFile file(uiFile);
                if (file.open(QIODevice::ReadOnly)) {
                    previous = QString::fromUtf8(file.readAll());
                }
                // solo nuestra barra (el usuario puede haber puesto otra) y
                // solo si es más antigua que la de Dolphin
                write = previous.contains(QLatin1String("separator_finder_")) && uiRcVersion(previous) < shippedVersion;
            }

            bool written = true;
            static const QRegularExpression toolBar(QStringLiteral("<ToolBar[^>]*name=\"mainToolBar\"[^>]*>.*?</ToolBar>"),
                                                    QRegularExpression::DotMatchesEverythingOption);
            if (const QRegularExpressionMatch match = toolBar.match(xml); write && match.hasMatch()) {
                xml.replace(match.capturedStart(), match.capturedLength(), QString::fromUtf8(DolphinToolBar));
                xml = mergeActionProperties(xml, previous);
                QDir().mkpath(QFileInfo(uiFile).absolutePath());
                QSaveFile out(uiFile);
                const QByteArray data = xml.toUtf8();
                written = out.open(QIODevice::WriteOnly) && out.write(data) == data.size() && out.commit();
                if (!written) {
                    qWarning() << "GoldenGlass: cannot write" << uiFile << out.errorString();
                }
            }
            if (written) {
                finder.writeEntry("DolphinUiVersion", shippedVersion);
            } else {
                done = false;
            }
        }
    }

    if (!firstRun) {
        styleConfig->sync();
        return;
    }

    // no status bar, icon-only toolbar buttons and small icons in the list.
    // Through the shared config: the platform theme has it open already and
    // Dolphin's settings read that same instance
    KSharedConfig::Ptr dolphinConfig = KSharedConfig::openConfig(QStringLiteral("dolphinrc"));
    KConfigGroup general = dolphinConfig->group(QStringLiteral("General"));
    if (!general.hasKey("ShowStatusBar")) {
        general.writeEntry("ShowStatusBar", QStringLiteral("Disabled"));
    }
    KConfigGroup toolBarGroup = dolphinConfig->group(QStringLiteral("MainWindow")).group(QStringLiteral("Toolbar mainToolBar"));
    if (!toolBarGroup.hasKey("ToolButtonStyle")) {
        toolBarGroup.writeEntry("ToolButtonStyle", QStringLiteral("IconOnly"));
    }
    KConfigGroup details = dolphinConfig->group(QStringLiteral("DetailsMode"));
    for (const char *key : {"IconSize", "PreviewSize"}) {
        if (!details.hasKey(key)) {
            details.writeEntry(key, Tokens::FinderListIconSize);
        }
    }
    done = dolphinConfig->sync() && done;

    // list view with Finder's columns: name, size, kind and date. Dolphin
    // keeps the properties of all folders in an extended attribute of this
    // directory (or in its .directory, which it reads first and removes after
    // the next save); it creates them without a view mode
    const QString globalProps = dataDir + QStringLiteral("/dolphin/view_properties/global");
    const QString dotDirectory = globalProps + QStringLiteral("/.directory");
    bool hasViewMode = false;
    QByteArray attributeProps;
    if (QFile::exists(dotDirectory)) {
        KConfig props(dotDirectory, KConfig::SimpleConfig);
        hasViewMode = props.group(QStringLiteral("Dolphin")).hasKey("ViewMode");
    } else {
        const QByteArray path = QFile::encodeName(globalProps);
        const char attribute[] = "user.kde.fm.viewproperties#1";
        const ssize_t size = getxattr(path.constData(), attribute, nullptr, 0);
        if (size > 0) {
            QByteArray value(size, Qt::Uninitialized);
            if (getxattr(path.constData(), attribute, value.data(), value.size()) > 0) {
                attributeProps = value;
                hasViewMode = value.contains("ViewMode=");
            }
        }
    }
    if (!hasViewMode) {
        QDir().mkpath(globalProps);
        // the .directory goes first: it starts from what the attribute holds
        // (sorting, hidden files…), so only the view mode and columns change
        if (!attributeProps.isEmpty()) {
            QFile file(dotDirectory);
            done = file.open(QIODevice::WriteOnly | QIODevice::Truncate) && file.write(attributeProps) == attributeProps.size() && done;
        }
        KConfig props(dotDirectory, KConfig::SimpleConfig);
        KConfigGroup dolphin = props.group(QStringLiteral("Dolphin"));
        dolphin.writeEntry("Version", 4);
        dolphin.writeEntry("ViewMode", 1);
        dolphin.writeEntry("VisibleRoles",
                           QStringList{QStringLiteral("Details_text"),
                                       QStringLiteral("Details_size"),
                                       QStringLiteral("Details_type"),
                                       QStringLiteral("Details_modificationtime"),
                                       QStringLiteral("CustomizedDetails")});
        done = props.sync() && done;
    }

    if (done) {
        finder.writeEntry("DolphinDefaults", DolphinDefaultsVersion);
    }
    styleConfig->sync();
}

}
