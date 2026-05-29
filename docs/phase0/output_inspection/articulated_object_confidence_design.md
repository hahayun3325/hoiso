# Articulated Object Confidence Design

## Motivation

A hard component threshold works for rigid objects like a SPAM can, but it is not suitable for articulated objects.

Articulated objects may naturally contain multiple meaningful parts.

## Rigid-object rule

For rigid objects:

lower component count is usually better

Example:

components = 1, largest_face_ratio = 1.0

is high confidence.

## Articulated-object rule

For articulated objects, the confidence should compare the predicted components with the expected part structure.

## Suggested formula

C_complete_artic =  w_ratio * largest_face_ratio+ w_count * exp(-abs(N_components - N_expected))+ w_balance * part_size_balance+ w_joint * joint_consistency

## Interpretation

The goal is not always one component.

The goal is the correct number of stable, meaningful parts with plausible joints.

## Proposal implication

HOLDSE-Flow should use object-type-aware confidence:

- rigid object: prefer one coherent component,
- articulated object: prefer stable part decomposition,
- bimanual articulated object: additionally check joint limits and contact consistency.  
