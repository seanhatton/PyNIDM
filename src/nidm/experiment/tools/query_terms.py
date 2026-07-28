"""Registry of natural-language query terms -> direct NIDM/BIDS predicates.

Some NIDM facts are stored as *direct predicates* on entities rather than as
``nidm:DataElement`` / ``nidm:PersonalDataElement`` nodes.  For example
``bidsmri2nidm`` / ``csv2nidm`` write, on the imaging acquisition object::

    niiri:...  nidm:Task "rest"^^xsd:string ;
               bids:session_number "1"^^xsd:string ;
               nidm:AcquisitionObject 1 ;          # run number
               nfo:filename "bids::...bold.nii.gz" .

These are genuine NIDM-ontology terms, but they have no ``nidm:sourceVariable``,
so queryai's DataElement resolver cannot find them and a question like
"what tasks are in this data?" silently drops the ``task`` variable.

This module maps common query phrasings to the predicate URI they denote so
queryai can resolve them.  The predicates below correspond one-for-one to the
``slot_uri`` values declared in ``src/nidm/experiment/schema/nidm_schema.yaml``
(the source of truth) -- e.g. ``AcquisitionObject.task -> nidm:Task``,
``Session.session_number -> bids:session_number`` -- plus a few BIDS
scan-metadata predicates the tools write as raw triples.
"""
import re

# Canonical namespaces (kept in sync with nidm.core.Constants).
_NIDM = "http://purl.org/nidash/nidm#"
_BIDS = "http://bids.neuroimaging.io/"
_NFO = "http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#"

# term (lower-case) -> (qname, full_uri).  Terms mirror the schema slot_uris.
_REGISTRY = {
    # -- schema-modeled predicates -----------------------------------------
    "task": ("nidm:Task", _NIDM + "Task"),
    "tasks": ("nidm:Task", _NIDM + "Task"),
    "session": ("bids:session_number", _BIDS + "session_number"),
    "sessions": ("bids:session_number", _BIDS + "session_number"),
    "ses": ("bids:session_number", _BIDS + "session_number"),
    "session number": ("bids:session_number", _BIDS + "session_number"),
    "session_number": ("bids:session_number", _BIDS + "session_number"),
    "run": ("nidm:AcquisitionObject", _NIDM + "AcquisitionObject"),
    "runs": ("nidm:AcquisitionObject", _NIDM + "AcquisitionObject"),
    "file": ("nfo:filename", _NFO + "filename"),
    "files": ("nfo:filename", _NFO + "filename"),
    "filename": ("nfo:filename", _NFO + "filename"),
    "filenames": ("nfo:filename", _NFO + "filename"),
    "modality": ("nidm:hadAcquisitionModality", _NIDM + "hadAcquisitionModality"),
    "acquisition modality": (
        "nidm:hadAcquisitionModality",
        _NIDM + "hadAcquisitionModality",
    ),
    "contrast": ("nidm:hadImageContrastType", _NIDM + "hadImageContrastType"),
    "contrast type": ("nidm:hadImageContrastType", _NIDM + "hadImageContrastType"),
    "image contrast": ("nidm:hadImageContrastType", _NIDM + "hadImageContrastType"),
    "usage": ("nidm:hadImageUsageType", _NIDM + "hadImageUsageType"),
    "usage type": ("nidm:hadImageUsageType", _NIDM + "hadImageUsageType"),
    "image usage": ("nidm:hadImageUsageType", _NIDM + "hadImageUsageType"),
    # -- curated BIDS scan-metadata (written as raw triples) ----------------
    "echo time": ("bids:EchoTime", _BIDS + "EchoTime"),
    "echotime": ("bids:EchoTime", _BIDS + "EchoTime"),
    "flip angle": ("bids:FlipAngle", _BIDS + "FlipAngle"),
    "flipangle": ("bids:FlipAngle", _BIDS + "FlipAngle"),
    "phase encoding direction": (
        "bids:PhaseEncodingDirection",
        _BIDS + "PhaseEncodingDirection",
    ),
    "phase encoding": (
        "bids:PhaseEncodingDirection",
        _BIDS + "PhaseEncodingDirection",
    ),
    "slice timing": ("bids:SliceTiming", _BIDS + "SliceTiming"),
}


def query_term_registry():
    """Return ``{term: {"qname": curie, "uri": full_uri}}`` for every
    direct-predicate query term."""
    return {t: {"qname": q, "uri": u} for t, (q, u) in _REGISTRY.items()}


def resolve_query_term(name):
    """Resolve a natural-language *name* to a direct-predicate descriptor.

    Returns ``{"term": matched_term, "qname": curie, "uri": full_uri}`` or
    ``None``.  Matching is case-insensitive on the whole phrase first, then
    falls back to individual words (so "the task" / "functional task" match
    ``task``).
    """
    if not name:
        return None
    key = name.strip().lower()
    if key in _REGISTRY:
        qname, uri = _REGISTRY[key]
        return {"term": key, "qname": qname, "uri": uri}
    for word in reversed(re.findall(r"[a-z_]+", key)):
        if word in _REGISTRY:
            qname, uri = _REGISTRY[word]
            return {"term": word, "qname": qname, "uri": uri}
    return None


__all__ = ["query_term_registry", "resolve_query_term"]
