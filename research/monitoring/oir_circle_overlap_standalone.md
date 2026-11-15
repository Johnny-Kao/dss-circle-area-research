# ASTM SCD DSS: OIR circle overlap test scenario

## Overview

Tests the DSS operational intent reference search API when a small circular
query overlaps a larger registered circular OIR near its boundary. A second,
ordinary circle well inside the registered OIR is a positive control.
All genuinely overlapping OIRs must be discoverable under ASTM F3548-21
DSS0005,2; additional search results are permitted.

The test places up to four circular OIRs, one at a time, relative to the
configured PlanningAreaResource. Each OIR is queried with 1 m circles from
several bearings. Only fixtures contained within the configured planning area
are used. A planning area that cannot support a valid fixture produces a test
configuration execution error, not a passing DSS result.

## Resources

### dss

A client to a DSS instance with ASTM F3548-21 Strategic Coordination permission
to create, search for, and delete operational intent references.

### id_generator

An `IDGeneratorResource` supplying a test OIR ID.

### planning_area

A `PlanningAreaResource` specifying where to place the test circles.

## Setup test case

### Clear previous test OIR test step

Remove a reference left by an earlier run, if any.

#### 🛑 Operational intent references can be queried by ID check

A reference must either be returned or be absent under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Operational intent reference removed check

Removing a previously existing reference must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Overlapping circular OIR is discoverable test case

### Create circular OIR test step

Create one accepted circular OIR with valid overlapping time and altitude bounds.

#### 🛑 Create operational intent reference query succeeds check

Creating a valid OIR must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Discover boundary-overlapping OIR test step

Use 1 m query circles near the OIR boundary, each with genuine horizontal,
altitude, and time overlap.

#### ⚠️ Boundary overlap is discoverable check

The overlapping reference must be discovered under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Ordinary contained circle discovers OIR test step

A 200 m circle well inside the registered OIR, with matching time and altitude,
must discover the OIR.

#### ⚠️ Ordinary contained circle discovers OIR check

The overlapping reference must be discovered under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Delete circular OIR test step

Delete the created reference using its returned OVN.

#### 🛑 Delete operational intent reference query succeeds check

Deleting the reference must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### Clean up test OIR test step

Delete any remaining OIR left after an early termination.

#### ⚠️ Operational intent references can be queried by ID check

The reference should be returned or absent under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Operational intent reference removed check

A remaining reference should be removable with the correct OVN under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.
