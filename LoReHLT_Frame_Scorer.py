#!/usr/bin/env python3

__author__ = "Oleg Aulov (oleg.aulov@nist.gov), Marion Le Bras (marion.lebras@nist.gov)"
__version__ = "Development: 0.9.5"
__date__ = "07/15/2019"

################################################################################
# MAIN
################################################################################

import os
import sys
import argparse
import pandas as pd
import numpy as np
import re

from sklearn.metrics import precision_score, recall_score, f1_score


from lib.lorehlt19helper import (
    boolean_gravity,
    numeric_gravity,
    getReference,
    getsubmission,
    correctkbids,
    genMAPMAR_results,
    genNDCG,
    genNDCGplot,
    genSEC_results,
    getreferenceNDCG,
    genNDCG_results,
    precisionN,
    genprecisionN_results,
    genpr_dt,
    genpr_dtp,
    genpr_dtps,
    genpr_dtpsu,
    genpr_dtpsr,
    genpr_dtpsur,
    plotpr,
)

gravity_choices = {"numeric": numeric_gravity, "boolean": boolean_gravity}
ndcgmethod_choices = {"method0": 0, "method1": 1}

def define_parser():
    """CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Generates PR curves for the LORELEI speech evaluation"
    )
    parser.add_argument("-s", "--system-output", help="Path to the system output", required=True)
    parser.add_argument(
        "-g", "--ground-truth", help="Path to the ground truth directory", required=True
    )
    parser.add_argument("-e", "--edl-subm", help="Path to the EDL submission file", required=False)
    parser.add_argument("-r", "--edl-ref", help="Path to the EDL reference file", required=False)

    parser.add_argument(
        "--gravity",
        choices=list(gravity_choices.keys()),
        default="boolean",
        help="specifies the type of gravity function",
    )

    parser.add_argument(
        "--ndcgmethod",
        choices=list(ndcgmethod_choices.keys()),
        default="method0",
        help="specifies the nDCG logarithm discounting method. Defaults to 0. Set to 1 to match LoReHLT evaluation plan.",
    )

    parser.add_argument(
        "-l", "--filelist", help="Path to the ground truth directory", required=False
    )
    parser.add_argument(
        "-o", "--output-directory", help="Path to save the evaluation output", required=True
    )
    parser.add_argument("-m", "--system-name", help="Name of the SF system", required=True)
    parser.add_argument(
        "-p", "--filename-prefix", help="prefix for output files", required=False, default=""
    )
    parser.add_argument(
        "-k",
        "--skip_sec",
        help="If present will skip diagnostic metrics of SEC",
        required=False,
        action="store_true",
    )
    parser.add_argument(
        "--nonils",
        help="If present will remove nil KBIDs from reference and submission",
        required=False,
        action="store_true",
    )

    parser.add_argument(
        "--altref",
        help="If present will use the oposite annotator's reference then what the random choice draws.",
        required=False,
        action="store_true",
    )

    parser.add_argument(
        "-t", "--system-threshold", help="Threshold", required=False, default=0, type=float
    )

    parser.add_argument(
        "--computepr",
        help="If present will compute Precision, Recall, F1 and generate PR Curves for different equivalence classes.",
        required=False,
        action="store_true",
    )

    return parser


def main():
    debug = False

    args = define_parser().parse_args()
    print(args)
    print("skipsec is: ", str(args.skip_sec))

    referencePath = args.ground_truth
    referenceFilelist = args.filelist
    systemPath = args.system_output
    outputDir = args.output_directory
    systemName = args.system_name
    threshold = args.system_threshold
    fnprefix = args.filename_prefix
    skipsecflag = args.skip_sec
    altrefflag = args.altref
    nonils = args.nonils
    computepr = args.computepr
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

    gravity_func = gravity_choices[args.gravity]
    ndcgmethod = ndcgmethod_choices[args.ndcgmethod]

    referenceTable = getReference(
        path=referencePath, gravity=gravity_func, filelist=referenceFilelist, altref=altrefflag, nonils=nonils
    )


# get threshold from the end of the json filename
    if threshold == 0.0:
        print("No threshold specified on the command line. Attempting to extract from submission filename.")
        parsedThreshold = re.findall(r"[\d]+\.[\d]+$",os.path.basename(systemPath).split(".json")[0])
        if len(parsedThreshold) > 0:
            print("Threshold value present in filename: ", os.path.basename(systemPath))
            threshold = float(parsedThreshold[0])
        else:
            print("No threshold present in filename. Using 0.0")


    systemTable = getsubmission(
        filename=systemPath, gravity=gravity_func, filelist=referenceFilelist, threshold=threshold, nonils=nonils
    )
    systemTable = correctkbids(systemTable, referenceTable)

    if not skipsecflag:
        genSEC_results(
            os.path.join(outputDir, fnprefix + "_diagnostic_SEC_scores.txt"),
            referenceTable,
            referencePath,
            systemTable,
            edl_ref=args.edl_ref,
            edl_subm=args.edl_subm,
        )

    referenceNDCG = getreferenceNDCG(referenceTable)
    myndcg, k = genNDCG(referenceNDCG, systemTable, breakties="standard", method=ndcgmethod)
    genNDCG_results(
        os.path.join(outputDir, fnprefix + "standard_nDCG_Scores.txt"), systemName, myndcg, k
    )
    genNDCGplot(
        os.path.join(outputDir, fnprefix + "standard_curve_nDCG" + ".pdf"), systemName, k, myndcg
    )

    myndcg, k = genNDCG(referenceNDCG, systemTable, breakties="vindictive", method=ndcgmethod)
    genNDCG_results(
        os.path.join(outputDir, fnprefix + "vindictive_nDCG_Scores.txt"), systemName, myndcg, k
    )
    genNDCGplot(
        os.path.join(outputDir, fnprefix + "vindictive_curve_nDCG" + ".pdf"), systemName, k, myndcg
    )

    myndcg, k = genNDCG(referenceNDCG, systemTable, breakties="forgiving", method=ndcgmethod)
    genNDCG_results(
        os.path.join(outputDir, fnprefix + "forgiving_nDCG_Scores.txt"), systemName, myndcg, k
    )
    genNDCGplot(
        os.path.join(outputDir, fnprefix + "forgiving_curve_nDCG" + ".pdf"), systemName, k, myndcg
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


    if computepr:
    # Precision/Recall Curves:

        referenceTable = getReference(
            path=referencePath, gravity=boolean_gravity, filelist=referenceFilelist, altref=altrefflag, nonils=nonils
        )
        systemTable = getsubmission(
            filename=systemPath, gravity=boolean_gravity, filelist=referenceFilelist, nonils=nonils
        )

        systemTable = correctkbids(systemTable, referenceTable)




        merged = genpr_dt(systemTable,referenceTable, threshold)
        header='"Type" Precision-Recall curve for {}'.format(systemName)
        plotpr(os.path.join(outputDir, fnprefix + "prcurveType.pdf"), merged, header, sysname=systemName)

        filename = os.path.join(outputDir, fnprefix + "F1_Type.txt")
        with open(filename, "w") as F_results_file:
            F_results_file.write("F1_Type:\t" + str(f1_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Precision_Type:\t" + str(precision_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Recall_Type:\t" + str(recall_score(merged.label, merged.pred)) + "\n")


        merged = genpr_dtp(systemTable,referenceTable, threshold)
        header='"Type+Place" Precision-Recall curve for {}'.format(systemName)
        plotpr(os.path.join(outputDir, fnprefix + "prcurveTypePlace.pdf"), merged, header, sysname=systemName)

        filename = os.path.join(outputDir, fnprefix + "F1_TypePlace.txt")
        with open(filename, "w") as F_results_file:
            F_results_file.write("F1_TypePlace:\t" + str(f1_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Precision_TypePlace:\t" + str(precision_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Recall_TypePlace:\t" + str(recall_score(merged.label, merged.pred)) + "\n")


        merged = genpr_dtps(systemTable,referenceTable, threshold)
        header='"Type+Place+Status" Precision-Recall curve for {}'.format(systemName)
        plotpr(os.path.join(outputDir, fnprefix + "prcurveTypePlaceStatus.pdf"), merged, header, sysname=systemName)

        filename = os.path.join(outputDir, fnprefix + "F1_TypePlaceStatus.txt")
        with open(filename, "w") as F_results_file:
            F_results_file.write("F1_TypePlaceStatus:\t" + str(f1_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Precision_TypePlaceStatus:\t" + str(precision_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Recall_TypePlaceStatus:\t" + str(recall_score(merged.label, merged.pred)) + "\n")


        merged = genpr_dtpsu(systemTable,referenceTable, threshold)
        header='"Type+Place+Status+Urgency" Precision-Recall curve for {}'.format(systemName)
        plotpr(os.path.join(outputDir, fnprefix + "prcurveTypePlaceStatusUrgency.pdf"), merged, header, sysname=systemName)

        filename = os.path.join(outputDir, fnprefix + "_F1_TypePlaceStatusUrgency.txt")
        with open(filename, "w") as F_results_file:
            F_results_file.write("F1_TypeTypePlaceStatusUrgency:\t" + str(f1_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Precision_TypePlaceStatusUrgency:\t" + str(precision_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Recall_TypePlaceStatusUrgency:\t" + str(recall_score(merged.label, merged.pred)) + "\n")


        merged = genpr_dtpsr(systemTable,referenceTable, threshold)
        header='"Type+Place+Status+Resolution" Precision-Recall curve for {}'.format(systemName)
        plotpr(os.path.join(outputDir, fnprefix + "prcurveTypePlaceStatusResolution.pdf"), merged, header, sysname=systemName)

        filename = os.path.join(outputDir, fnprefix + "_F1_TypePlaceStatusResolution.txt")
        with open(filename, "w") as F_results_file:
            F_results_file.write("F1_TypePlaceStatusResolution:\t" + str(f1_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Precision_TypePlaceStatusResolution:\t" + str(precision_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Recall_TypePlaceStatusResolution:\t" + str(recall_score(merged.label, merged.pred)) + "\n")


        merged = genpr_dtpsur(systemTable,referenceTable, threshold)
        header='"Type+Place+Status+Urgency+Resolution" Precision-Recall curve for {}'.format(systemName)
        plotpr(os.path.join(outputDir, fnprefix + "prcurveTypePlaceStatusUrgencyResolution.pdf"), merged, header, sysname=systemName)

        filename = os.path.join(outputDir, fnprefix + "_F1_TypePlaceStatusUrgencyResolution.txt")
        with open(filename, "w") as F_results_file:
            F_results_file.write("F1_TypePlaceStatusUrgencyResolution:\t" + str(f1_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Precision_TypePlaceStatusUrgencyResolution:\t" + str(precision_score(merged.label, merged.pred)) + "\n")
            F_results_file.write("Recall_TypePlaceStatusUrgencyResolution:\t" + str(recall_score(merged.label, merged.pred)) + "\n")



    print("Success!")


if __name__ == "__main__":
    main()
