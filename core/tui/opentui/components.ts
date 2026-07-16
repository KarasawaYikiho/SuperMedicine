import { BoxRenderable, MouseButton, TextRenderable } from "@opentui/core"
import { THEME } from "./theme.ts"

export function createText(renderer, options) {
  return new TextRenderable(renderer, {
    fg: THEME.text,
    height: 1,
    width: "100%",
    ...options,
  })
}

export function createNavigationItem(renderer, route, state, activateRoute) {
  const item = new BoxRenderable(renderer, {
    id: `nav-${route.id}`,
    width: "100%",
    height: 1,
    focusable: true,
    backgroundColor: THEME.surface,
    onMouseOver() {
      state.hoveredRoute = route.id
      item.backgroundColor = THEME.hover
      renderer.setMousePointer("pointer")
      renderer.requestRender()
    },
    onMouseOut() {
      state.hoveredRoute = null
      item.backgroundColor = state.currentRoute === route.id ? THEME.surfaceRaised : THEME.surface
      renderer.setMousePointer("default")
      renderer.requestRender()
    },
    onMouseUp(event) {
      if (event.button !== MouseButton.LEFT) return
      event.stopPropagation()
      item.focus()
      activateRoute(route.id)
    },
    onKeyDown(event) {
      if (event.name !== "enter" && event.name !== "return") return
      event.preventDefault()
      activateRoute(route.id)
    },
  })
  const label = createText(renderer, { id: `nav-label-${route.id}`, content: "" })
  item.add(label)

  const update = () => {
    const active = state.currentRoute === route.id
    label.content = `${active ? "●" : " "} ${route.symbol} ${route.label}`
    label.fg = active ? THEME.accent : THEME.text
    if (state.hoveredRoute !== route.id) {
      item.backgroundColor = active ? THEME.surfaceRaised : THEME.surface
    }
  }
  item.on("focused", () => {
    if (label.isDestroyed) return
    label.fg = THEME.accent
    renderer.requestRender()
  })
  item.on("blurred", () => {
    if (!label.isDestroyed) update()
  })
  update()
  return { item, update }
}

export function createPanel(renderer, options = {}) {
  return new BoxRenderable(renderer, {
    border: true,
    borderColor: THEME.border,
    backgroundColor: THEME.surface,
    ...options,
  })
}

export function createActionButton(renderer, { id, label, onActivate }) {
  let hovered = false
  const button = createPanel(renderer, {
    id,
    width: "100%",
    height: 3,
    focusable: true,
    paddingX: 1,
    focusedBorderColor: THEME.accent,
    onMouseOver() {
      hovered = true
      button.backgroundColor = THEME.hover
      renderer.setMousePointer("pointer")
      renderer.requestRender()
    },
    onMouseOut() {
      hovered = false
      button.backgroundColor = THEME.surface
      renderer.setMousePointer("default")
      renderer.requestRender()
    },
    onMouseUp(event) {
      if (event.button !== MouseButton.LEFT) return
      event.stopPropagation()
      button.focus()
      onActivate()
    },
    onKeyDown(event) {
      if (event.name !== "enter" && event.name !== "return") return
      event.preventDefault()
      onActivate()
    },
  })
  const text = createText(renderer, { content: label, fg: THEME.accent })
  button.add(text)
  button.on("blurred", () => {
    if (!hovered && !button.isDestroyed) button.backgroundColor = THEME.surface
  })
  return button
}

export function createListItem(renderer, { id, label, onActivate = () => {} }) {
  const item = new BoxRenderable(renderer, {
    id,
    width: "100%",
    height: 1,
    focusable: true,
    backgroundColor: THEME.surface,
    onMouseOver() {
      item.backgroundColor = THEME.hover
      renderer.setMousePointer("pointer")
      renderer.requestRender()
    },
    onMouseOut() {
      if (!item.focused) item.backgroundColor = THEME.surface
      renderer.setMousePointer("default")
      renderer.requestRender()
    },
    onMouseUp(event) {
      if (event.button !== MouseButton.LEFT) return
      event.stopPropagation()
      item.focus()
      onActivate()
    },
    onKeyDown(event) {
      if (event.name !== "enter" && event.name !== "return") return
      event.preventDefault()
      onActivate()
    },
  })
  const text = createText(renderer, { content: `› ${label}` })
  item.add(text)
  item.on("focused", () => {
    if (item.isDestroyed || text.isDestroyed) return
    text.fg = THEME.accent
    item.backgroundColor = THEME.surfaceRaised
    renderer.requestRender()
  })
  item.on("blurred", () => {
    if (item.isDestroyed || text.isDestroyed) return
    text.fg = THEME.text
    item.backgroundColor = THEME.surface
    renderer.requestRender()
  })
  return item
}
