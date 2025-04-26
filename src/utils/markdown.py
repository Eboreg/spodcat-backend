import re

from markdown import Markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor


class LinkTargetPostprocessor(Postprocessor):
    def run(self, text):
        def sub(m: re.Match):
            a: str = m.group(0)
            if not re.search(r" target=", a):
                return a.replace("<a ", "<a target=\"_blank\" ")
            return a

        return re.sub(r"<a .*?href=\"http.*?>", sub, text)


class MarkdownExtension(Extension):
    def extendMarkdown(self, md: Markdown):
        md.postprocessors.register(LinkTargetPostprocessor(md), "link-target", 100)
