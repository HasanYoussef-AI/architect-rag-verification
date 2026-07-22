"""A minimal, dependency-free DOM for the EUR-Lex Official Journal HTML.

Structural units are located by their ELI anchors, so unit boundaries must come
from element nesting rather than from a regex window between anchors. A regex
window silently over-captures whenever an anchor is the last of its kind, which
would append an entire Annex to the final Article.

Built on the standard library's HTMLParser rather than lxml or BeautifulSoup, to
keep ingestion free of a parsing dependency whose version could change how the
corpus chunks.
"""

from __future__ import annotations

from html.parser import HTMLParser

# Elements that never have a closing tag.
VOID_TAGS = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)

# Elements whose content is not document text.
SKIP_TAGS = frozenset({"script", "style"})

# Elements that introduce a block boundary when flattening to text.
BLOCK_TAGS = frozenset(
    {
        "p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6",
        "table", "tbody", "thead", "td", "th", "br", "hr", "blockquote",
    }
)


class Element:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: dict[str, str], parent: "Element | None" = None):
        self.tag = tag
        self.attrs = attrs
        self.children: list[Element | str] = []
        self.parent = parent

    @property
    def id(self) -> str | None:
        return self.attrs.get("id")

    def iter_elements(self):
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.iter_elements()

    def find_by_id(self, element_id: str) -> "Element | None":
        for element in self.iter_elements():
            if element.id == element_id:
                return element
        return None

    def index_by_id(self) -> dict[str, "Element"]:
        """First element for each id, in document order."""
        found: dict[str, Element] = {}
        for element in self.iter_elements():
            eid = element.id
            if eid is not None and eid not in found:
                found[eid] = element
        return found

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Element {self.tag} id={self.id!r} children={len(self.children)}>"


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("[document]", {})
        self._stack = [self.root]
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if self._skip_depth:
            if tag in SKIP_TAGS:
                self._skip_depth += 1
            return
        if tag in SKIP_TAGS:
            self._skip_depth = 1
            return
        element = Element(tag, {k: (v or "") for k, v in attrs}, self._stack[-1])
        self._stack[-1].children.append(element)
        if tag not in VOID_TAGS:
            self._stack.append(element)

    def handle_startendtag(self, tag: str, attrs) -> None:
        if self._skip_depth or tag in SKIP_TAGS:
            return
        element = Element(tag, {k: (v or "") for k, v in attrs}, self._stack[-1])
        self._stack[-1].children.append(element)

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            if tag in SKIP_TAGS:
                self._skip_depth -= 1
            return
        if tag in VOID_TAGS:
            return
        # Close back to the matching open tag, tolerating unclosed elements.
        for depth in range(len(self._stack) - 1, 0, -1):
            if self._stack[depth].tag == tag:
                del self._stack[depth:]
                return

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._stack[-1].children.append(data)


def parse_html(source: str) -> Element:
    builder = _TreeBuilder()
    builder.feed(source)
    builder.close()
    return builder.root
