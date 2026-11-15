# ASTM F3548-21 DSS: Circular OIR overlap search test scenario

## Overview

Tests the DSS operational intent reference search API when a small query circle
overlaps a larger registered circle close to its boundary.

The scenario places up to four accepted circular operational intent references
(OIRs), one at a time, within the configured `PlanningAreaResource`. Each OIR
is searched for using a 1 m circle overlapping its boundary and an ordinary
circle contained well inside it. An overlapping OIR must be returned under ASTM
F3548-21 DSS0005,2; additional search results are permitted.

The planning area must have sufficient horizontal and vertical room for the
test circles. If no valid overlap can be constructed, the scenario reports a
test configuration error rather than a DSS conformance result.

## Resources

### dss

Client to a DSS instance with ASTM F3548-21 Strategic Coordination permission,
used to create, search for, and delete operational intent references.

### id_generator

An `IDGeneratorResource` supplying the test OIR ID.

### planning_area

A `PlanningAreaResource` specifying where to place the test circles.

## Setup test case

### Clear previous test OIR test step

Remove an OIR left by a previous run, if present.

#### 🛑 Operational intent references can be queried by ID check

The reference must either be returned or be absent under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Operational intent reference removed check

Removing a previously existing reference must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Overlapping circular OIR is discoverable test case

### Create circular OIR test step

Create one accepted circular OIR with valid time and altitude bounds.
Repeat for each selected placement within the planning area.

#### 🛑 Create operational intent reference query succeeds check

Creating the OIR must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Discover boundary-overlapping OIR test step

A 1 m query circle overlapping the registered OIR near its boundary must
discover the OIR when the time and altitude intervals also overlap.

#### ⚠️ Boundary overlap is discoverable check

The overlapping reference must be discovered under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Ordinary contained circle discovers OIR test step

An ordinary query circle contained well inside the registered OIR must
discover the OIR when the time and altitude intervals also overlap.

#### 🛑 Ordinary contained circle discovers OIR check

The overlapping reference must be discovered under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Delete circular OIR test step

Delete the registered OIR using its returned OVN.

#### 🛑 Delete operational intent reference query succeeds check

Deleting the OIR with the correct OVN must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### Clean up test OIR test step

Delete any remaining OIR after an error or early termination.

#### ⚠️ Operational intent references can be queried by ID check

The reference should be returned or absent under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Operational intent reference removed check

Deleting a remaining OIR with the correct OVN should succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.
