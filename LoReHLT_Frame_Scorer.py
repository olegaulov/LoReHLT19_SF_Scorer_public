#!/usr/bin/env python3

__author__ = "Oleg Aulov (oleg.aulov@nist.gov), Marion Le Bras (marion.lebras@nist.gov)"
__version__ = "Development: 0.9"
__date__ = "07/02/2019"

################################################################################
# MAIN
################################################################################


import argparse
from lib.lorehlt19helper import *
from lib.sec_helper import get_SEC_ref, SEC_scoring

if __name__ == "__main__":

    debug = False

    # argument parser ----------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Generates PR curves for the LORELEI speech evaluation"
    )
    parser.add_argument(
        "-s", "--system-output", help="Path to the system output", required=True
    )
    parser.add_argument(
        "-g", "--ground-truth", help="Path to the ground truth directory", required=True
    )
    parser.add_argument(
        "-e", "--edl-subm", help="Path to the EDL submission file", required=False
    )
    parser.add_argument(
        "-r", "--edl-ref", help="Path to the EDL reference file", required=False
    )
    parser.add_argument(
        "-l", "--filelist", help="Path to the ground truth directory", required=False
    )
    parser.add_argument(
        "-o",
        "--output-directory",
        help="Path to save the evaluation output",
        required=True,
    )
    parser.add_argument(
        "-m", "--system-name", help="Name of the SF system", required=True
    )
    parser.add_argument(
        "-p",
        "--filename-prefix",
        help="prefix for output files",
        required=False,
        default="",
    )
    parser.add_argument(
        "-t",
        "--system-threshold",
        help="Threshold",
        required=False,
        default=0,
        type=float,
    )

    args = parser.parse_args()
    # print (args)

    referencePath = args.ground_truth
    referenceFilelist = args.filelist
    systemPath = args.system_output
    outputDir = args.output_directory
    systemName = args.system_name
    threshold = args.system_threshold
    fnprefix = args.filename_prefix
    # create output directory
    try:
        if not os.path.exists(outputDir):
            os.makedirs(outputDir)
    except:
        sys.exit("CAN NOT CREATE OUTPUT DIRECTORY: " + outputDir)

    # basic error checks -------------------------------------------------------
    if not os.path.exists(referencePath):
        sys.exit("PATH NOT FOUND: " + referencePath)

    if not os.path.exists(systemPath):
        sys.exit("PATH NOT FOUND: " + systemPath)

    referenceTable = getReference(
        path=referencePath, gravity=advanced_gravity, filelist=referenceFilelist
    )
    systemTable = getsubmission(
        filename=systemPath, gravity=advanced_gravity, filelist=referenceFilelist
    )
    systemTable = correctkbids(systemTable, referenceTable)

    genSEC_results(os.path.join(outputDir, fnprefix + "diagnostic_SEC_scores.txt"), referenceTable, referencePath, systemTable)


    referenceNDCG = getreferenceNDCG(referenceTable)
    myndcg, k = genNDCG(referenceNDCG, systemTable, breakties="standard")
    genNDCG_results(
        os.path.join(outputDir, fnprefix + "standard_nDCG_Scores.txt"),
        systemName,
        myndcg,
        k,
    )
    genNDCGplot(
        os.path.join(outputDir, fnprefix + "standard_curve_nDCG" + ".pdf"),
        systemName,
        k,
        myndcg,
    )

    myndcg, k = genNDCG(referenceNDCG, systemTable, breakties="vindictive")
    genNDCG_results(
        os.path.join(outputDir, fnprefix + "vindictive_nDCG_Scores.txt"),
        systemName,
        myndcg,
        k,
    )
    genNDCGplot(
        os.path.join(outputDir, fnprefix + "vindictive_curve_nDCG" + ".pdf"),
        systemName,
        k,
        myndcg,
    )

    myndcg, k = genNDCG(referenceNDCG, systemTable, breakties="forgiving")
    genNDCG_results(
        os.path.join(outputDir, fnprefix + "forgiving_nDCG_Scores.txt"),
        systemName,
        myndcg,
        k,
    )
    genNDCGplot(
        os.path.join(outputDir, fnprefix + "forgiving_curve_nDCG" + ".pdf"),
        systemName,
        k,
        myndcg,
    )

    genMAPMAR_results(
        os.path.join(outputDir, fnprefix + "DiagnosticScores.txt"),
        systemName,
        referenceTable,
        systemTable,
    )

    myprecisionN = precisionN(referenceNDCG, systemTable)
    genprecisionN_results(
        os.path.join(outputDir, fnprefix + "precisionN.txt"), systemName, myprecisionN
    )

    referenceTable = getReference(
        path=referencePath, gravity=gravity, filelist=referenceFilelist
    )
    systemTable = getsubmission(
        filename=systemPath, gravity=gravity, filelist=referenceFilelist
    )
    systemTable = correctkbids(systemTable, referenceTable)

    systemTable_dt = systemTable[["DocumentID", "Type"]]
    systemTable_dt = systemTable_dt.drop_duplicates()
    referenceTable_dt = referenceTable[["doc_id", "type"]]
    referenceTable_dt = referenceTable_dt.drop_duplicates()

    merged = pd.merge(
        systemTable_dt,
        referenceTable_dt,
        left_on=["DocumentID", "Type"],
        right_on=["doc_id", "type"],
        how="inner",
    )
    merged = merged.drop_duplicates()

    try:
        myprecision = merged.shape[0] / systemTable_dt.shape[0]
    except ZeroDivisionError:
        myprecision = 0
    try:
        myrecall = merged.shape[0] / referenceTable_dt.shape[0]
    except ZeroDivisionError:
        myrecall = 0
    try:
        myf1 = 2 * ((myprecision * myrecall) / (myprecision + myrecall))
    except ZeroDivisionError:
        myf1 = 0

    filename = os.path.join(outputDir, fnprefix + "_F1_type.txt")

    with open(filename, "w") as F_results_file:
        F_results_file.write("F1_Type:\t" + str(myf1) + "\n")
        F_results_file.write("Precision_Type:\t" + str(myprecision) + "\n")
        F_results_file.write("Recall_Type:\t" + str(myrecall) + "\n")

    systemTable_dtp = systemTable[["DocumentID", "Type", "Place_KB_ID"]]
    systemTable_dtp = systemTable_dtp.drop_duplicates()
    referenceTable_dtp = referenceTable[["doc_id", "type", "kb_id"]]
    referenceTable_dtp = referenceTable_dtp.drop_duplicates()

    merged = pd.merge(
        systemTable_dtp,
        referenceTable_dtp,
        left_on=["DocumentID", "Type", "Place_KB_ID"],
        right_on=["doc_id", "type", "kb_id"],
        how="inner",
    )
    merged = merged.drop_duplicates()

    try:
        myprecision = merged.shape[0] / systemTable_dtp.shape[0]
    except ZeroDivisionError:
        myprecision = 0
    try:
        myrecall = merged.shape[0] / referenceTable_dtp.shape[0]
    except ZeroDivisionError:
        myrecall = 0
    try:
        myf1 = 2 * ((myprecision * myrecall) / (myprecision + myrecall))
    except ZeroDivisionError:
        myf1 = 0

    filename = os.path.join(outputDir, fnprefix + "_F1_type_place.txt")

    with open(filename, "w") as F_results_file:
        F_results_file.write("F1_TypePlace:\t" + str(myf1) + "\n")
        F_results_file.write("Precision_TypePlace:\t" + str(myprecision) + "\n")
        F_results_file.write("Recall_TypePlace:\t" + str(myrecall) + "\n")

    print("Success!")
