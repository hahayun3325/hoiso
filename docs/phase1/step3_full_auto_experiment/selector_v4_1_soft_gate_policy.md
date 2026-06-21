# selector-v4.1 soft contact gate policy

## Motivation

The selector should choose the most useful candidate for the next optimization stage. It should not treat every penetration as final failure, because contact-aware optimization is expected to repair pose/contact errors.

## Main role

Selector-v4.1 selects the best candidate according to:

1. object shape coherence
2. object reconstruction quality
3. contact proximity
4. recoverability by later contact-aware optimization

## Hard reject conditions

A candidate is hard rejected if:

- the mesh is missing;
- the object is extremely floating;
- the object is severely fragmented or incoherent;
- the object has extreme scale/bbox failure;
- the hand is almost completely trapped inside the object.

## Warning conditions

A candidate receives a warning, not hard rejection, if:

- max penetration depth is high;
- moderate penetration ratio exists;
- contact is close but physically imperfect;
- object integrity is imperfect but still recoverable.

## Output labels

- `selected_clean`
- `selected_with_warning`
- `selected_for_contact_aware_optimization`
- `reject_and_rerun`
- `failed_after_rerun`

## Important interpretation

Max penetration depth is a warning and a contact-aware optimization target, not always a hard reject.
