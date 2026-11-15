# ASTM SCD DSS: OIR circle overlap test scenario

## Overview

Tests that the DSS search API discovers a circular operational intent reference
when a small circular query genuinely overlaps its boundary. Search must return
every overlapping reference under ASTM F3548-21 DSS0005,2; additional references
are permitted, so this scenario does not test their absence.

The scenario creates up to six circular OIRs one at a time within the
configured PlanningAreaResource. Their small query circles overlap genuine
circular boundaries, with cases selected from distinct spatial grid cells and
edge directions. A PlanningAreaResource that cannot support at least two
distinct valid cases produces a test configuration execution error rather than
a passing conformance result.

## Resources

### dss

A client to a DSS instance with ASTM F3548-21 Strategic Coordination
permission, used to create, search for, and delete operational intent references.

### id_generator

An `IDGeneratorResource` supplying the test OIR ID.

### planning_area

A `PlanningAreaResource` specifying where to place the test circles.

## Setup test case

### Clear previous test OIR test step

Remove a reference left by a previous run, if present.

#### 🛑 Operational intent references can be queried by ID check

The reference must either be returned or be absent under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Operational intent reference removed check

Removing a previously existing reference must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Overlapping circular OIR is discoverable test case

### Create circular OIR test step

Create an accepted circular OIR with valid time and altitude bounds.

#### 🛑 Create operational intent reference query succeeds check

Creating the valid OIR must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Discover boundary-overlapping OIR test step

Search using a small circle that genuinely overlaps the registered circle near
its boundary, with overlapping time and altitude ranges.

#### ⚠️ Boundary overlap is discoverable check

The overlapping OIR must be returned under
**[astm.f3548.v21.DSS0005,2](../../../../requirements/astm/f3548/v21.md)**.

### Delete circular OIR test step

Delete the created OIR using its returned OVN.

#### 🛑 Delete operational intent reference query succeeds check

Deleting the OIR must succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### Clean up test OIR test step

Delete the known OIR ID after an error or early termination.

#### ⚠️ Operational intent references can be queried by ID check

The reference should be returned or absent under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Operational intent reference removed check

Deleting a remaining OIR with the correct OVN should succeed under
**[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.
