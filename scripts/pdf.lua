-- Pandoc filter for `make pdf`: adapts the web-only parts of a post for LaTeX.
--
--   <div class="embed"><iframe src=...>   -> "Video: <link>" paragraph
--   other raw HTML (<br>, etc.)           -> dropped
--   [text]{.margin-note}                  -> footnote
--   /images/foo.jpg                       -> static/images/foo.jpg
--
-- Must run before --citeproc so citations inside margin notes still resolve.

local function embed_link(src)
  local id = src:match("youtube[%w%-]*%.com/embed/([%w_%-]+)")
  if id then return "https://www.youtube.com/watch?v=" .. id end
  return src
end

local function Div(el)
  if not el.classes:includes("embed") then return nil end
  local src
  el:walk({
    RawBlock = function(raw) src = src or raw.text:match('src="([^"]+)"') end,
    RawInline = function(raw) src = src or raw.text:match('src="([^"]+)"') end,
  })
  if not src then return {} end
  local url = embed_link(src)
  return pandoc.Para({ pandoc.Emph({ pandoc.Str("Video: "), pandoc.Link(url, url) }) })
end

local function drop_html(el)
  if el.format == "html" then return {} end
end

local function Span(el)
  if el.classes:includes("margin-note") then
    return pandoc.Note({ pandoc.Para(el.content) })
  end
end

local function Image(el)
  if el.src:sub(1, 8) == "/images/" then
    el.src = "static" .. el.src
    return el
  end
end

-- Second pass: remove the space before a footnote mark, so "fails.1" not "fails. 1".
local function tighten_notes(ils)
  for i = #ils, 2, -1 do
    if ils[i].t == "Note" and (ils[i - 1].t == "Space" or ils[i - 1].t == "SoftBreak") then
      ils:remove(i - 1)
    end
  end
  return ils
end

return {
  { Div = Div },
  { RawBlock = drop_html, RawInline = drop_html, Span = Span, Image = Image },
  { Inlines = tighten_notes },
}
