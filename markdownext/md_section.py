# -*- coding: utf-8 -*-
import re
from markdown import Extension
from markdown.blockprocessors import BlockProcessor
from markdown.util import etree


class SectionProcessor(BlockProcessor):
    RE = re.compile(ur'^([^\s]+?)::---+$', re.DOTALL)

    def test(self, parent, block):
        self.m = SectionProcessor.RE.search(block)
        return bool(self.m)

    def run(self, parent, blocks):
        blocks.pop(0)
        itemprop = self.m.group(1)

        blocks_in_section = []
        while len(blocks):
            if SectionProcessor.RE.search(blocks[0]):
                break
            blocks_in_section.append(blocks.pop(0))
        section = etree.SubElement(parent, 'div')
        section.set('itemprop', itemprop)
        section.set('class', 'section')
        self.parser.parseBlocks(section, blocks_in_section)


class SectionExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.parser.blockprocessors.add('section',
                                      SectionProcessor(md.parser),
                                      '<empty')
