---
type: "query"
date: "2026-08-29T03:55:20.183199+00:00"
question: "Why does classify_offer() connect Offer identity tests to Apple Watch parsing, Parser worker sync, Offer identity core, Offer title cleanup, Device field parsers, Junk section glue rules?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["classify_offer()", "sync_folder()", "parse_apple_watch()", "OfferIdentity"]
---
w
# Q: Why does classify_offer() connect Offer identity tests to Apple Watch parsing, Parser worker sync, Offer identity core, Offer title cleanup, Device field parsers, Junk section glue rules?

## Answer

classify_offer() is a dispatcher in offer_identity.py:L2876. Community detection placed it in Offer identity tests because 68 test functions call it. Production: sync_folder() calls it at sync.py:L195. It EXTRACTED-calls specialists: Offer identity core (22: asis_tier, normalize_iphone_model, infer_sim), Device field parsers (10: extract_color/storage/ram, parse_android, parse_galaxy_watch), Offer title cleanup (7: clean_offer_title, is_junk_offer, parse_audio/camera), Junk section glue (4: should_prepend_section, is_junk_section via 2 hops, strip_part_marker), Apple Watch (1: parse_apple_watch). Clustering split one file into specialty communities; the hub stitches them. Tests-as-home-community is a Louvain artifact, not a layering bug.

## Outcome

- Signal: useful

## Source Nodes

- classify_offer()
- sync_folder()
- parse_apple_watch()
- OfferIdentity