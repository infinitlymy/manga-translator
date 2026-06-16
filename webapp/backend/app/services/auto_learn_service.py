import logging
from collections import Counter
from datetime import datetime, timezone
from sqlmodel import Session, select
from app.models.base import Collection, Dictionary, TextRegion

logger = logging.getLogger(__name__)

# How many times a source→target pair must appear before auto-learning
MIN_OCCURRENCE_THRESHOLD = 2


def save_text_regions(session: Session, job_id: str, asset_id: str, collection_id: str | None, text_regions: list):
    """Persist text regions extracted from a translation result."""
    regions = []
    for region in text_regions:
        if not region.text:
            continue
        bbox = None
        if hasattr(region, "xyxy"):
            bbox = {"x": float(region.xyxy[0]), "y": float(region.xyxy[1]),
                    "w": float(region.xyxy[2] - region.xyxy[0]),
                    "h": float(region.xyxy[3] - region.xyxy[1])}
        tr = TextRegion(
            job_id=job_id,
            asset_id=asset_id,
            collection_id=collection_id,
            source_text=region.text,
            translated_text=getattr(region, "translation", None) or "",
            confidence=getattr(region, "text_confident", None),
            bbox=bbox,
        )
        session.add(tr)
        regions.append(tr)
    session.commit()
    return regions


def run_auto_learn(session: Session, collection_id: str, job_id: str):
    """Analyze text regions from the given job and auto-create dictionary entries for consistent mappings."""
    coll = session.get(Collection, collection_id)
    if not coll:
        logger.warning(f"Collection {collection_id} not found for auto-learn")
        return

    # Fetch all text regions for this collection that are not yet auto-learned
    stmt = (
        select(TextRegion)
        .where(TextRegion.collection_id == collection_id)
        .where(TextRegion.auto_learned == False)
    )
    regions = session.exec(stmt).all()

    if not regions:
        return

    # Group by source text and count translated_text occurrences
    source_groups: dict[str, Counter] = {}
    for r in regions:
        if not r.translated_text:
            continue
        # Normalize whitespace
        src = " ".join(r.source_text.split())
        tgt = " ".join(r.translated_text.split())
        if src not in source_groups:
            source_groups[src] = Counter()
        source_groups[src][tgt] += 1

    newly_created = 0
    for source_text, counter in source_groups.items():
        most_common = counter.most_common(1)[0]
        target_text, count = most_common
        if count < MIN_OCCURRENCE_THRESHOLD:
            continue

        # Skip if already exists in dictionary for this scope
        exists = _dictionary_exists(session, coll, source_text, target_text)
        if exists:
            continue

        # Determine best scope: series > artist > collection
        scope_series = coll.series
        scope_artist = coll.artist
        scope_collection = coll.id

        # Prefer broader scopes for short terms (likely names/places)
        # Prefer collection scope for longer terms (likely context-specific)
        if scope_series and len(source_text) <= 10:
            series = scope_series
            artist = None
            collection_id_for_dict = None
            note = f"Auto-learned from {count} occurrences in series '{scope_series}'"
        elif scope_artist and len(source_text) <= 10:
            series = None
            artist = scope_artist
            collection_id_for_dict = None
            note = f"Auto-learned from {count} occurrences in artist '{scope_artist}'"
        else:
            series = None
            artist = None
            collection_id_for_dict = scope_collection
            note = f"Auto-learned from {count} occurrences in collection"

        entry = Dictionary(
            collection_id=collection_id_for_dict,
            series=series,
            artist=artist,
            pattern=source_text,
            replacement=target_text,
            phase="post",
            auto_learned=True,
            usage_count=count,
            note=note,
        )
        session.add(entry)
        newly_created += 1
        logger.info(f"Auto-learned dictionary entry: '{source_text}' -> '{target_text}' ({note})")

    if newly_created:
        session.commit()

    # Mark processed regions as auto_learned
    for r in regions:
        r.auto_learned = True
        session.add(r)
    session.commit()
    logger.info(f"Auto-learn: created {newly_created} entries from {len(regions)} regions in collection {collection_id}")


def _dictionary_exists(session: Session, coll: Collection, source: str, target: str) -> bool:
    """Check if an equivalent dictionary entry already exists for this collection/series/artist."""
    stmt = select(Dictionary).where(
        (Dictionary.pattern == source) &
        (Dictionary.replacement == target) &
        (
            (Dictionary.is_global == True) |
            (Dictionary.collection_id == coll.id) |
            (Dictionary.series == coll.series) |
            (Dictionary.artist == coll.artist)
        )
    )
    return session.exec(stmt).first() is not None
