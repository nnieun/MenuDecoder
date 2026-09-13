"""Resolve which menu item(s) a chat message is about.

Moved out of provider.py so graph.py (provider-agnostic) can use it to
decide, before generating a reply, whether an item still needs describe()/
images() run on it - without importing a concrete provider module.
"""
import re
import unicodedata

# Shared between backend/provider.py, backend/mock.py (both append this exact
# warning when images() found nothing) and graph.py (checks for it below to
# tell "never tried" apart from "tried, found nothing" - images stays [] in
# both cases, so the list alone can't distinguish them).
NO_IMAGE_FOUND_WARNING = '참고 사진을 찾지 못했어요.'


def needs_images(item) -> bool:
    return not item.images and NO_IMAGE_FOUND_WARNING not in item.warnings


def _normalize(value: str) -> str:
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value).casefold())


def resolve_targets(analysis, message):
    """Resolve explicit names first, then unambiguous conversational references."""
    valid = {item.item_id for item in analysis.items}
    if message.referenced_item_ids:
        return [item_id for item_id in message.referenced_item_ids if item_id in valid]
    content = _normalize(message.content)
    matches = [item.item_id for item in analysis.items
               if any(_normalize(name) and _normalize(name) in content
                      for name in (item.original_name, item.translated_name))]
    if matches:
        return matches
    if len(analysis.items) == 1:
        return [analysis.items[0].item_id]
    if any(word in content for word in ('그거', '그음식', '그메뉴', '그것', '아까', 'it', 'that')):
        for previous in reversed(analysis.messages):
            if previous.message_id == message.message_id or previous.status != 'done':
                continue
            targets = [item_id for item_id in previous.referenced_item_ids if item_id in valid]
            if targets:
                return targets if len(targets) == 1 else []
    return []
