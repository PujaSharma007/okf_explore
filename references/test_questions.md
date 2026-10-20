---
type: Reference
title: "Test questions"
description: "15 questions with expected answers for testing the bundle."
tags: [safety, reference]
status: draft
---

# Test Questions and Expected Answers

## Simple lookups

### Question 1
What PPE is required for welding?

Expected answer:
- welding-fumes -> respirator
- arc-radiation -> welding-helmet
- burns -> welding-helmet, safety-boots

Source: hazards_catalog.md, ppe_matrix.csv

### Question 2
Which hazard is associated with grinding that requires hearing protection?

Expected answer:
- high-noise -> hearing-protection

Source: hazards_catalog.md, ppe_matrix.csv
Official reference: https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95

### Question 3
Which PPE is associated with chemical-exposure?

Expected answer:
- respirator
- chemical-gloves
- safety-glasses
- safety-boots

Source: hazards_catalog.md, ppe_matrix.csv

### Question 4
Which hazard is associated with roof-work?

Expected answer:
- fall-from-height

Source: work_activities.md

### Question 5
Which rule covers trench-collapse?

Expected answer:
- excavation-safety

Source: hazards_catalog.md, safety_rules.md
Official reference: https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.652

## Reverse questions

### Question 6
Which work types need hearing-protection?

Expected answer:
- grinding

Reason: grinding is associated with high-noise.

Source: ppe_matrix.csv

### Question 7
Which hazards are protected against by respirator?

Expected answer:
- welding-fumes
- chemical-exposure

Source: ppe_catalog.md

### Question 8
Which work types involve fall-from-height?

Expected answer:
- roof-work
- excavation

Source: hazards_catalog.md

### Question 9
Which hazards are associated with chemical-gloves?

Expected answer:
- chemical-exposure
- burns

Source: ppe_catalog.md

### Question 10
Which work types involve burns?

Expected answer:
- welding
- grinding
- chemical-handling

Source: hazards_catalog.md

## Multi-step questions

### Question 11
Which rule covers the main hazard of roof-work, and what PPE is associated with it?

Expected answer:
- roof-work -> fall-from-height
- fall-from-height -> fall-protection
- fall-from-height -> safety-harness

Official reference:
https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.501

### Question 12
Which PPE protects against the main grinding particle hazard, and which rule applies?

Expected answer:
- grinding -> flying-particles
- flying-particles -> safety-glasses
- flying-particles -> eye-face-protection

Official reference:
https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.133

### Question 13
Which work type involves welding-fumes, what PPE is associated with this hazard, and which rule applies?

Expected answer:
- welding -> welding-fumes
- welding-fumes -> respirator
- welding-fumes -> respiratory-protection

Official reference:
https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.134

### Question 14
Which work type involves trench-collapse, which rule applies, and which PPE is associated with the hazard?

Expected answer:
- excavation -> trench-collapse
- trench-collapse -> excavation-safety
- trench-collapse -> hard-hat, safety-boots

Official reference:
https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.652

### Question 15
Which work type involves chemical-exposure, what PPE is associated with the hazard, and which rule addresses respiratory protection?

Expected answer:
- chemical-handling -> chemical-exposure
- chemical-exposure -> respirator, chemical-gloves, safety-glasses, safety-boots
- chemical-exposure -> respiratory-protection

Official references:
https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.1200
https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.134