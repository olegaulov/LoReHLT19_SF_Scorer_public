# LoReHLT 2019 Situation Frame Scorer

Date 07/15/2019

This package includes the system output scorer for the LoReHLT
Situation Frame (SF) Evalaution task for year 2019.  The release includes the Python script `LoReHLT_Frame_Scorer.py`, which validates and scores SF system output files.


Below is an example command that would run the scoring script acainst a SF system output json file named 2019_CMN_system_output.json. 

```bash
LoReHLT_Frame_Scorer.py                  \
    -s /Data/2019_CMN_system_output.json \
    -g /Data/DryRun/CMN                  \
    -o /Data/Scores/                     \
    -m SF_Primary_System                 \
    -p ILCMN_CP1_all                     \
    -e /Data/2019_EDL_system_output.tab  \
    -r /Data/DryRun/EDL_ref.tab
```

A collection of unit test cases is under development and will be included in future releases.

The scoring script performs the following steps:
  - JSON validation
  - Ingestion of reference files
  - Scoring (note that output files will be overwritten on subsequent
    runs without prompt)
  - Exits with status of 0 if scoring was succesful, and 1 otherwise


## Usage parameters

* `-h`: will display the usage help message, regardless of other arguments
* `-s submission_file` (required): the path to the tab delimited submission, i.e. system output.  
* `-g ground_truth_directory` (required): Ground truth tab delimited files are expected to be in the directory. This directory is expected to contain "needs", and "issues" subdirectories as well as possibly "speech", and "sentiments".
* `-o output_directory` (required): The scorer output files are written to this directory.
* `-m system_name` (required): specifies the SF system name.
* `-p prefix` (defaults to no prefix): the prefix given to the output file names 
* `-e edl_submission -r edl_reference` (required to output correct SEC scores): the tab delimited submission for the matching EDL submission, and the corresponding reference EDL file. Both files are used to resolve the submission NIL-ids to the corresponding reference ids. The scorer will run without `-e` and `-r` but will not be able to resolve the NIL ids if these parameteres are not given.
* `--gravity {numeric,boolean}` (defaults to `boolean`)
* `-k` skips SEC diagnostic metrics


## Setup

  The LoReHLT_Frame_Scorer.py is a Python script and requires:

* Python version 3.6.0 or later,
* Numpy version 1.13.3 or later,
* Pandas version 0.22.0 or later,
* Matplotlib 2.1.0 or later,
* Jsonschema 2.6.0 or later
* sklearn
* xlrd

## Changelog

  07/15/19 (0.9.5):

    - Added SEC tests
    - Added resolution of NIL clustered entities that are a source
      of SEC, against the EDL annotation

  07/03/19 (0.9):

    - Initial development release of LORELEI SF Scorer for 2019
      based on the 2018 scorer

## Authors

  Oleg Aulov <oleg.aulov@nist.gov>
  Marion Le Bras <marion.lebras@nist.gov>


## Copyright

  Full details can be found at: http://nist.gov/data/license.cfm

  This software was developed at the National Institute of Standards
  and Technology by employees of the Federal Government in the course
  of their official duties.  Pursuant to Title 17 Section 105 of the
  United States Code this software is not subject to copyright
  protection within the United States and is in the public domain.
  NIST assumes no responsibility whatsoever for its use by any party,
  and makes no guarantees, expressed or implied, about its quality,
  reliability, or any other characteristic.

  We would appreciate acknowledgement if the software is used.  This
  software can be redistributed and/or modified freely provided that
  any derivative works bear some notice that they are derived from it,
  and any modified versions bear some notice that they have been
  modified.

  THIS SOFTWARE IS PROVIDED "AS IS."  With regard to this software,
  NIST MAKES NO EXPRESS OR IMPLIED WARRANTY AS TO ANY MATTER
  WHATSOEVER, INCLUDING MERCHANTABILITY, OR FITNESS FOR A PARTICULAR
  PURPOSE.

