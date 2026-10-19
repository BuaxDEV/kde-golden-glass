/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <QHash>
#include <QObject>
#include <QPersistentModelIndex>
#include <QPointer>
#include <QRectF>
#include <QStyleOption>

#include <functional>

class QApplication;
class QListView;
class QPainter;
class QToolBar;
class QToolButton;
class QVariantAnimation;

namespace GoldenGlass
{
class Helper;

//* Dolphin as the macOS 27 Finder (tokens [finder]):
//* - main windows of the IntegratedTitleBarApps have no KWin title bar (the
//*   decoration drops it); the toolbar takes the first row and draws the
//*   traffic lights over the sidebar column, which reaches the top
//* - toolbar buttons grouped in glass capsules, with a segmented control that
//*   slides its pill and Liquid Glass press feedback
//* - the location shows only the current folder, as a title
//* - sidebar selection as a gray pill that slides between places
//* - details view with rounded alternate stripes and a Finder-like header
//* - the first time Dolphin runs with GoldenGlass, Finder defaults (toolbar,
//*   list view, no status bar) unless the user already changed them
class Finder : public QObject
{
    Q_OBJECT

public:
    explicit Finder(Helper &helper, std::function<bool(const QWidget *)> isTranslucent, std::function<void(QWidget *)> updateBlur, QObject *parent);
    ~Finder() override;

    //* reads the app list and the active KWin decoration
    void loadConfiguration();

    //* decides whether this app gets the Finder look; applies the first-run defaults
    void polishApplication(QApplication *app);
    void polishPalette(QPalette &palette) const;
    void polish(QWidget *widget);
    void unpolish(QWidget *widget);

    bool isActive() const
    {
        return _active;
    }

    //* toolbar that spans the sidebar column (and holds the traffic lights)
    bool isFinderToolBar(const QWidget *widget) const;
    //* tool button drawn as a capsule segment
    bool isFinderToolButton(const QWidget *widget) const;
    //* breadcrumb of the Finder toolbar (shows only the current folder)
    bool isFinderNavigator(const QWidget *widget) const;
    //* window without KWin title bar (the toolbar draws the traffic lights)
    bool isIntegratedWindow(const QWidget *window) const;

    int toolBarItemMargin() const;
    //* height of a place in the sidebar (-1: not Finder's sidebar)
    int sidebarItemHeight(const QWidget *widget) const;
    QSize toolButtonSize(const QStyleOptionToolButton *option, const QWidget *widget) const;

    //* painting; each one returns false when the element is not Finder's
    bool drawToolBarBackground(const QStyleOption *option, QPainter *painter, const QWidget *widget) const;
    bool drawToolButton(const QStyleOptionToolButton *option, QPainter *painter, const QWidget *widget) const;
    bool drawItemViewItem(const QStyleOptionViewItem *option, QPainter *painter, const QWidget *widget) const;
    bool drawHeader(const QStyleOptionHeader *option, QPainter *painter, const QWidget *widget) const;
    bool drawNavigatorButton(const QWidget *widget) const;
    bool drawDockSeparator(const QStyleOption *option, QPainter *painter, const QWidget *widget) const;
    //* search field moved into the toolbar (PE_PanelLineEdit and PE_FrameLineEdit)
    bool drawSearchField(const QStyleOption *option, QPainter *painter, const QWidget *widget, bool frame) const;

protected:
    bool eventFilter(QObject *object, QEvent *event) override;

private:
    enum class Light {
        None = -1,
        Close,
        Minimize,
        Zoom
    };

    //* a run of toolbar buttons between separators, in toolbar coordinates
    struct Group {
        QList<QToolButton *> buttons;
        QRect rect;
        bool segmented = false;
        bool navigation = false;
    };

    //* animated state of one tool button
    struct ButtonState {
        bool hovered = false;
        bool pressed = false;
        QVariantAnimation *hover = nullptr;
        QVariantAnimation *press = nullptr;
    };

    //* the sliding pill of a segmented control
    struct Pill {
        QPointer<QToolButton> current;
        QRectF from;
        QRectF to;
        QVariantAnimation *slide = nullptr;
        QList<QPointer<QToolButton>> buttons;
    };

    //* traffic lights of a toolbar
    struct Lights {
        bool hovered = false;
        Light pressed = Light::None;
        QVariantAnimation *glyphs = nullptr;
    };

    //* sliding selection of a sidebar
    struct SidebarSelection {
        QPersistentModelIndex index;
        QRectF from;
        QRectF to;
        QVariantAnimation *slide = nullptr;
    };

    Group groupFor(const QToolButton *button) const;
    ButtonState &buttonState(const QWidget *button) const;
    Pill &pillFor(const Group &group) const;
    QRectF pillRect(const Group &group, const QToolButton *button) const;

    //* traffic light centers, in toolbar coordinates
    QPointF lightCenter(const QWidget *toolBar, Light light) const;
    Light lightAt(const QWidget *toolBar, const QPointF &position) const;
    QRectF lightsRect(const QWidget *toolBar) const;
    void renderLights(QPainter *painter, const QWidget *toolBar) const;
    void triggerLight(QWidget *window, Light light) const;

    //* the toolbar starts where the sidebar ends (or after the traffic lights)
    void updateToolBarMargins(QWidget *window) const;
    //* invisible widget in front of the buttons, as wide as the sidebar
    QWidget *ensureLeadSpacer(QToolBar *toolBar) const;
    //* Dolphin's search field goes into the toolbar, in place of the magnifier
    void updateSearch(QWidget *bar) const;
    //* only the current folder of the breadcrumb stays visible
    void updateNavigator(QWidget *navigator) const;

    bool eventFilterToolBar(QToolBar *toolBar, QEvent *event);
    //* updates the sidebar pill; true when it moved
    bool syncSidebarSelection(QListView *view) const;
    void paintSidebarSelection(QListView *view) const;
    void paintStripes(QWidget *viewport) const;

    QColor sidebarBackground(const QWidget *widget, const QPalette &palette, bool *clear) const;
    QColor token(unsigned int light, unsigned int dark, const QPalette &palette) const;

    void applyDolphinDefaults() const;

    Helper &_helper;
    std::function<bool(const QWidget *)> _isTranslucent;
    std::function<void(QWidget *)> _updateBlur;

    bool _active = false;
    bool _decorationIsOurs = false;

    mutable QHash<const QObject *, ButtonState> _buttons;
    mutable QHash<const QObject *, Pill> _pills;
    mutable QHash<const QObject *, Lights> _lights;
    mutable QHash<const QObject *, SidebarSelection> _sidebars;
    mutable bool _updatingNavigator = false;
    mutable bool _updatingSpacer = false;
};

}
