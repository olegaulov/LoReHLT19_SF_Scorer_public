__author__ = "Oleg Aulov (oleg.aulov@nist.gov), Marion Le Bras (marion.lebras@nist.gov)"
__version__ = "Development: 0.9.5"
__date__ = "07/15/2019"

import configparser
import csv
import glob
import os
import sys

import jsonschema
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import simplejson as json
from matplotlib.backends.backend_pdf import PdfPages
from pandas.io.json import json_normalize
from sklearn.metrics import average_precision_score, recall_score

from lib.sec_helper import get_SEC_ref, SEC_scoring, nil_mapper

import random
random.seed(a=1)

matplotlib.use("Agg")

try:
    config = configparser.ConfigParser()
    base_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(os.path.dirname(base_dir), "config.ini")) as f:
        config.readfp(f)
except:
    sys.exit("CAN NOT OPEN CONFIG FILE: " + os.path.join(os.path.dirname(base_dir), "config.ini"))


def getReference(path, gravity, filelist):
    speechref = getSpeechReference(path, gravity)
    if speechref is not None:
        reference = pd.concat([getTextReference(path, gravity), speechref])
    else:
        reference = getTextReference(path, gravity)
    if filelist:
        print("Reference filelist present. Subsetting...")
        try:
            myfiles = pd.read_csv(filelist, header=None)
        except:
            sys.exit("FAILED TO OPEN REFERENCE LIST FILE: " + filelist)
        reference = reference[reference["doc_id"].isin(myfiles[0])]
    return reference.reset_index(drop=True)


def getTextReference(path, gravity):
    # path = # use your path
    allFiles = glob.glob(path + "/needs/*.tab") + glob.glob(path + "/issues/*.tab")
    sentiment_files = glob.glob(path + "/sentiments/*.tab")
    # print(allFiles)
    reference = pd.DataFrame(
        columns=[
            "description",
            "doc_id",
            "frame_id",
            "frame_type",
            "issue_status",
            "issue_type",
            "kb_id",
            "need_status",
            "need_type",
            "place_id",
            "proxy_status",
            "reported_by",
            "resolution_status",
            "resolved_by",
            "scope",
            "severity",
            "user_id",
        ]
    )
    list_ = []
    for file_ in allFiles:
        df = pd.read_csv(
            file_,
            index_col=None,
            header=0,
            sep="\t",
            quoting=csv.QUOTE_NONE,
            dtype={"doc_id": object, "kb_id": object},
        )
        myannotator = random.choice(df.user_id.unique())
        df = df[df.user_id == myannotator]
        list_.append(df)
    if not list_:
        sys.exit("Text reference list is empty. Please check the reference folder and try again.")
    reference = reference.append(list_)
    d = {
        "1_discomfort": 1,
        "2_injury": 2,
        "3_possibledeath": 3,
        "4_certaindeath": 4,
        "none": 0,
        np.nan: 0,
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        0: 0,
    }
    reference["severity"] = reference["severity"].map(d)
    d = {
        "1_smallgroup": 1,
        "2_largegroup": 2,
        "3_municipality": 3,
        "4_region": 4,
        "none": 0,
        np.nan: 0,
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        0: 0,
    }
    reference["scope"] = reference["scope"].map(d)
    reference["status"] = reference[["need_status", "issue_status"]].apply(
        lambda x: x["need_status"] if pd.isnull(x["issue_status"]) else x["issue_status"], axis=1
    )
    reference["type"] = reference[["issue_type", "need_type"]].apply(
        lambda x: x["issue_type"] if pd.isnull(x["need_type"]) else x["need_type"], axis=1
    )
    reference.drop(
        [
            "need_status",
            "issue_status",
            "description",
            "issue_type",
            "need_type",
            "proxy_status",
            "reported_by",
            "resolved_by",
        ],
        axis=1,
        inplace=True,
    )
    reference = reference[reference["place_id"] != "none"]
    reference = reference[pd.notnull(reference["place_id"])]

    # d = {'True': True, 'False': False, np.nan: False}
    # reference['urgency_status'].replace(d, inplace = True)
    reference["urgent"] = reference[["scope", "severity"]].apply(
        lambda x: True if x["scope"] > 1 and x["severity"] > 1 else False, axis=1
    )

    d = {"insufficient": True, "sufficient": False, np.nan: False}
    reference["unresolved"] = reference["resolution_status"].map(d)

    d = {"current": True, "past": False, "future": False, "not_current": False, np.nan: False}
    reference["current"] = reference["status"].map(d)

    sentiment_df_list = []
    for file_ in sentiment_files:
        df = pd.read_csv(
            file_,
            index_col=None,
            header=0,
            sep="\t",
            quoting=csv.QUOTE_NONE,
            dtype={"doc_id": object, "kb_id": object},
            na_values=["none"],
        )
        sentiment_df_list.append(df)
    all_sentiments_df = pd.concat(sentiment_df_list, axis=0, ignore_index=True)
    # some frame ids are repeated, they need to be grouped
    grouped = all_sentiments_df.groupby(["doc_id", "target"])
    grouped_sentiments = grouped.aggregate(lambda x: tuple(x))
    # merge with reference on target<->frame_id
    reference = pd.merge(
        reference,
        grouped_sentiments,
        how="left",
        left_on=["doc_id", "frame_id"],
        right_on=["doc_id", "target"],
        suffixes=("", "_sentiment"),
    )
    reference["sentiments"] = reference["emotion_value"].str.split(",")
    reference["gravity"] = reference.apply(gravity, axis=1)
    reference["frame_count"] = 1
    reference = reference[
        [
            "doc_id",
            "frame_id",
            "kb_id",
            "user_id",
            "type",
            "urgent",
            "unresolved",
            "current",
            "gravity",
            "frame_count",
            "status",
        ]
    ]
    return reference


def getSpeechReference(path, gravity):
    allFiles = glob.glob(path + "/speech/*.tab")
    list_ = []
    for file_ in allFiles:
        df = pd.read_csv(file_, index_col=None, header=0, sep="\t", quoting=csv.QUOTE_NONE)
        list_.append(df)
    if not list_:
        print("Speech reference list is empty.")
        return None

    reference = pd.concat(list_)
    reference = reference[reference["situation_type"] != "out-of-domain"]
    d = {"Current": True, "Past Only": False, "Future": False, "not_current": False, np.nan: False}
    reference["current"] = reference["situation_status"].map(d)

    d = {
        "1_discomfort": 1,
        "2_injury": 2,
        "3_possibledeath": 3,
        "4_certaindeath": 4,
        "none": 0,
        "Severity_Not_Required": 0,
        np.nan: 0,
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        0: 0,
    }
    reference["severity"] = reference["severity"].map(d)
    d = {
        "1_smallgroup": 1,
        "2_largegroup": 2,
        "3_municipality": 3,
        "4_region": 4,
        "none": 0,
        "Scope_Not_Required" : 0,
        np.nan: 0,
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        0: 0,
    }
    reference["scope"] = reference["scope"].map(d)

    reference["urgent"] = reference[["scope", "severity"]].apply(
        lambda x: True if x["scope"] > 1 and x["severity"] > 1 else False, axis=1
    )

    d = {"Insufficent": True, "Insufficient/Unknown": True, "Sufficient": False, np.nan: False}
    reference["unresolved"] = reference["resolution_status"].map(d)
    reference = reference.rename(
        columns={"situation_id": "doc_id", "file_id": "frame_id", "situation_type": "type", "place_id": "kb_id"}
     )
    reference["frame_count"] = 1
    reference["user_id"] = "Appn1"
    issue_types = ["regimechange", "crimeviolence", "terrorism" ]
    reference["frame_type"] = reference["type"].apply(lambda x: "issue" if x in issue_types else "need")
    reference["emotion_value"] = np.NaN
    reference["gravity"] = reference.apply(gravity, axis=1)
    reference = reference[~reference["kb_id"].isnull()]
    reference = reference[reference["kb_id"] != "NIL"]

    reference = reference[
        [
            "doc_id",
            "frame_id",
            "kb_id",
            "user_id",
            "type",
            "urgent",
            "unresolved",
            "current",
            "gravity",
            "frame_count",
        ]
    ]
    return reference


def getsubmission(filename, gravity, filelist):
    base_dir = os.path.dirname(os.path.realpath(__file__))
    schemafile = os.path.join(
        os.path.dirname(base_dir), "schemas", "LoReHLT19-schema_V1.json"  # TODO update schema
    )
    try:
        with open(schemafile, "r") as f:
            schema_data = f.read()
            schema = json.loads(schema_data)
    except:
        sys.exit("CAN NOT OPEN JSON SCHEMA FILE: " + schemafile)

    try:
        with open(filename) as f:
            d = json.load(f)
    except:
        sys.exit("CAN NOT OPEN JSON SUBMISSION FILE: " + filename)

    try:
        jsonschema.validate(d, schema)
    except Exception as e:
        print(e)
        sys.exit("ERROR: System submission json failed validation:\n" + str(e) + "\n")

    mysubmission = pd.DataFrame(
        columns=[
            "Confidence",
            "DocumentID",
            "Justification_ID",
            "Place_KB_ID",
            "Resolution",
            "Status",
            "Type",
            "Urgent",
            "SEC",
        ]
    )
    mysubmission = mysubmission.append(json_normalize(d))

    d = {True: True, False: False, np.nan: False}
    mysubmission["urgent"] = mysubmission["Urgent"].map(d)
    mysubmission.drop("Urgent", axis=1, inplace=True)

    d = {"insufficient": True, "sufficient": False, np.nan: False}
    mysubmission["unresolved"] = mysubmission["Resolution"].map(d)

    d = {"current": True, "past": False, "future": False, "not_current": False, np.nan: False}
    mysubmission["current"] = mysubmission["Status"].map(d)

    issue_types = ["regimechange", "crimeviolence", "terrorism"]
    mysubmission["frame_type"] = mysubmission["Type"].apply(
        lambda x: "issue" if x in issue_types else "need"
    )

    mysubmission["gravity"] = mysubmission.apply(gravity, axis=1)
    mysubmission["frame_count"] = 1
    mysubmission["DocumentID"] = mysubmission["DocumentID"].str.rstrip(".txt")

    if filelist and (mysubmission.shape[0] > 0):
        print("Reference filelist present. Subsetting submission file...")
        try:
            myfiles = pd.read_csv(filelist, header=None)
        except:
            sys.exit("FAILED TO OPEN REFERENCE LIST FILE: " + filelist)
        mysubmission = mysubmission[mysubmission["DocumentID"].isin(myfiles[0])]
    return mysubmission


def dcg_at_k(r, k, method=0):
    r = np.asfarray(r)[:k]
    if r.size:
        if method == 0:
            return r[0] + np.sum(r[1:] / np.log2(np.arange(2, r.size + 1)))
        elif method == 1:
            return np.sum(r / np.log2(np.arange(2, r.size + 2)))
        else:
            raise ValueError("method must be 0 or 1.")
    return 0.0


# def ndcg_at_k(r, k, method=0):
#     dcg_max = dcg_at_k(sorted(r, reverse=True), k, method)
#     if not dcg_max:
#         return 0.
#     return dcg_at_k(r, k, method) / dcg_max


def ndcg_at_k(r, k, method=0):
    dcg_max = dcg_at_k(sorted(r["gain"], reverse=True), k, method)
    if not dcg_max:
        return 0.0
    return dcg_at_k(r["sysgain"], k, method) / dcg_max


def gain(row):
    if row["gravity"] >= int(config["GraveFrameCounts"]["HighGravity"]):
        return int(config["Gain"]["High"])
    elif (
        int(config["GraveFrameCounts"]["MediumGravity"])
        <= row["gravity"]
        < int(config["GraveFrameCounts"]["HighGravity"])
    ):
        return int(config["Gain"]["Medium"])
    else:
        return int(config["Gain"]["Low"])


def boolean_gravity(row):
    if row["current"] and row["unresolved"] and row["urgent"]:
        return True
    else:
        return False


def numeric_gravity(row):
    frame_type = row["frame_type"]
    try:
        sentiments = row["emotion_value"] if not pd.isna(row["emotion_value"]) else []
    except KeyError:
        sentiments = []
        for block in row["SEC"]:
            if block["Emotion_Anger"]:
                sentiments.append("anger")
            if block["Emotion_Fear"]:
                sentiments.append("fear")
        sentiments = list(set(sentiments))

    gravity = 0.0

    if frame_type == "need":
        if row["current"] and row["unresolved"] and row["urgent"]:
            gravity += 1
            if "fear" in sentiments:
                gravity += 0.2
            if "anger" in sentiments:
                gravity += 0.2

    elif frame_type == "issue":
        if row["current"] and row["urgent"]:
            gravity += 1
            if any(e in ["fear", "anger"] for e in sentiments):
                gravity += 0.2

    return gravity


def genTrue_TypePlace(row):  # type place
    if (
        (row["doc_id"] == row["DocumentID"])
        & (row["type"] == row["Type"])
        & (row["kb_id"] == row["Place_KB_ID"])
    ):
        return 1
    else:
        return 0


def genTrue_TypePlaceStatus(row):  # type place status
    if (
        (row["doc_id"] == row["DocumentID"])
        & (row["type"] == row["Type"])
        & (row["kb_id"] == row["Place_KB_ID"])
        & (row["current_y"] == row["current_x"])
    ):
        return 1
    else:
        return 0


def genTrue_TypePlaceStatusUrgency(row):  # type place status urgency
    if (
        (row["doc_id"] == row["DocumentID"])
        & (row["type"] == row["Type"])
        & (row["kb_id"] == row["Place_KB_ID"])
        & (row["current_y"] == row["current_x"])
        & (row["urgent_y"] == row["urgent_x"])
    ):
        return 1
    else:
        return 0


def genTrue_TypePlaceStatusResolution(row):  # type place status resolution
    if (
        (row["doc_id"] == row["DocumentID"])
        & (row["type"] == row["Type"])
        & (row["kb_id"] == row["Place_KB_ID"])
        & (row["current_y"] == row["current_x"])
        & (row["unresolved_y"] == row["unresolved_x"])
    ):
        return 1
    else:
        return 0


def genTrue_TypePlaceStatusUrgencyResolution(row):  # type place status urgency resolution
    if (
        (row["doc_id"] == row["DocumentID"])
        & (row["type"] == row["Type"])
        & (row["kb_id"] == row["Place_KB_ID"])
        & (row["current_y"] == row["current_x"])
        & (row["urgent_y"] == row["urgent_x"])
        & (row["unresolved_y"] == row["unresolved_x"])
    ):
        return 1
    else:
        return 0


# MAP
def mapmar(reference, system, genTrue):
    # np.seterr(all='raise')
    avgPrecision = []
    recall = []

    grouped = reference.groupby(["type", "kb_id"])

    for mygroup, KBsituation in grouped:

        sysKBsituation = system[
            (system["Place_KB_ID"] == str(mygroup[1])) & (system["Type"] == str(mygroup[0]))
        ]
        # keep only highest confidence frame for each input file
        sysKBsituation = sysKBsituation.drop_duplicates(
            subset=["DocumentID", "Place_KB_ID"], keep="first"
        )

        KBmergedAP = pd.merge(
            sysKBsituation, KBsituation, how="left", left_on=["DocumentID"], right_on=["doc_id"]
        )
        KBmergedAP = KBmergedAP.sort_values(by="Confidence", ascending=False, na_position="last")

        if not KBmergedAP.empty:
            # print("table not empty")
            KBmergedAP["true"] = KBmergedAP.apply(genTrue, axis=1)
            # print("AP true conf pairs:\n",(KBmergedAP.true, KBmergedAP.Confidence))
            if not (max(KBmergedAP.true) == 0):
                try:
                    myprecision = average_precision_score(KBmergedAP.true, KBmergedAP.Confidence)
                    # print("succeeded, adding to list")
                    avgPrecision.append(myprecision)
                    # print("avgprecision: ", myprecision)
                except FloatingPointError:
                    # print("caught exception, adding zero")
                    avgPrecision.append(0.0)
            else:
                # print("table empty AP 0")
                avgPrecision.append(0.0)
        else:
            # print("table empty AP 0")
            avgPrecision.append(0.0)

        KBmergedAR = pd.merge(
            sysKBsituation, KBsituation, how="right", left_on=["DocumentID"], right_on=["doc_id"]
        )
        KBmergedAR = KBmergedAR.sort_values(by="Confidence", ascending=False, na_position="last")
        KBmergedAR["true"] = 1
        KBmergedAR["returned"] = KBmergedAR.apply(genTrue, axis=1)
        KBmergedAR.Confidence.fillna(-1, inplace=True)
        # print(mygroup)
        myrecall = recall_score(KBmergedAR.true, KBmergedAR.returned)
        # print(myrecall)
        recall.append(myrecall)

    meanAP = np.mean(avgPrecision)
    macroAR = np.mean(recall)
    return meanAP, macroAR


def genNDCGplot(filename, sysname, k, myndcg):
    plt.scatter(k, myndcg, marker=".", s=10, linewidth=0.5, color="red")
    # plt.plot(k, myndcg, linestyle='-', color = "blue")
    plt.title("nDCG@k for " + sysname)
    plt.xlabel("k")
    plt.ylabel("nDCG")
    plt.grid()
    gc = plt.gcf()
    gc.set_size_inches(7, 7)
    # plt.legend(["dfbdfbdbdbd"], loc='upper right')
    pp = PdfPages(filename)
    pp.savefig(plt.gcf())
    pp.close()
    plt.close()
    return


def getreferenceNDCG(reference):
    refNDCG = (
        reference.groupby(["kb_id", "type"])[
            "urgent", "unresolved", "current", "gravity", "frame_count"
        ]
        .agg(["sum"])
        .reset_index()
    )
    refNDCG.columns = refNDCG.columns.droplevel(1)
    refNDCG = refNDCG.sort_values(by=["gravity", "frame_count"], ascending=False)
    refNDCG["gain"] = refNDCG.apply(gain, axis=1)
    refNDCG = refNDCG[refNDCG["kb_id"] != ""]
    return refNDCG


PAIRS_TO_MATCH_FRAMES = [
    (["doc_id", "kb_id", "type"], ["DocumentID", "Place_KB_ID", "Type"], "EqClass_Type+Place"),
    (
        ["doc_id", "kb_id", "type", "status"],
        ["DocumentID", "Place_KB_ID", "Type", "Status"],
        "EqClass_Type+Place+Status",
    ),
]


def genSEC(
    referenceTable,
    path_for_sentiments,
    systemTable,
    pairs_to_match_frames,
    edl_ref=None,
    edl_subm=None,
):

    mapping = nil_mapper(edl_subm, edl_ref) if edl_ref and edl_subm else None

    sec_ref = get_SEC_ref(path_for_sentiments)
    scores = [
        SEC_scoring(referenceTable, sec_ref, systemTable, ref_el=i, sub_el=j, mapping=mapping)
        for i, j, n in pairs_to_match_frames
    ]

    return scores


def genSEC_results(
    output_file,
    referenceTable,
    path_for_sentiments,
    systemTable,
    pairs_to_match_frames=PAIRS_TO_MATCH_FRAMES,
    **kwargs
):

    scores = genSEC(
        referenceTable, path_for_sentiments, systemTable, pairs_to_match_frames, **kwargs
    )
    header = [
        "EqClass",
        "PrecisionPolarity",
        "RecallPolarity",
        "F1Polarity",
        "PrecisionSentiment",
        "RecallSentiment",
        "F1Sentiment",
        "PrecisionEmotion",
        "RecallEmotion",
        "F1Emotion",
    ]
    with open(output_file, "w") as ofile:
        ofile.write("\t".join(header) + "\n")
        for a, b in zip(scores, pairs_to_match_frames):
            # PrecisionPolarity, RecallPolarity, F1Polarity, PrecisionSentiment, RecallSentiment, F1Sentiment, PrecisionEmotion, RecallEmotion, F1Emotion = a
            # ref_columns, sub_columns = b
            ofile.write("\t".join([b[2]] + [str(e) for e in a]) + "\n")


def genNDCG(referenceNDCG, systemTable, breakties=None):
    mysystem = (
        systemTable.groupby(["Place_KB_ID", "Type"])[
            "urgent", "unresolved", "current", "gravity", "frame_count"
        ]
        .agg(["sum"])
        .reset_index()
    )
    mysystem.columns = mysystem.columns.droplevel(1)
    if mysystem.shape[0] > 0:
        mysystem = mysystem[mysystem["Place_KB_ID"] != ""]
    merged = pd.merge(
        referenceNDCG[["kb_id", "type", "gain"]],
        mysystem,
        how="outer",
        left_on=["kb_id", "type"],
        right_on=["Place_KB_ID", "Type"],
    )

    merged.gravity = merged.gravity.fillna(0)
    merged.gain = merged.gain.fillna(0)
    merged.frame_count = merged.frame_count.fillna(0)
    merged["sysgain"] = merged.apply(
        lambda x: int(x["gain"]) if x["frame_count"] > 0 else 0, axis=1
    )
    if breakties == "forgiving":
        merged = merged.sort_values(by=["gravity", "sysgain"], ascending=False)
    elif breakties == "vindictive":
        merged = merged.sort_values(by=["gravity", "sysgain"], ascending=[False, True])
    elif breakties == "standard":
        merged = merged.sort_values(by=["gravity"], ascending=False)
    else:
        sys.exit("Error: Unrecognized nDCG tie breaking method: " + breakties)
    k = range(1, len(merged["gain"]) + 1)
    return [ndcg_at_k(merged, i) for i in k], k


def correctkbids(systemTable, referenceTable):
    def kbidcorrector(row):
        currentfile = referenceTable[
            (referenceTable["doc_id"] == row["DocumentID"])
            & (referenceTable["type"] == row["Type"])
            & (referenceTable.kb_id.str.contains("\|") == True)
        ]
        if len(currentfile.index) > 0:
            for _, refrow in currentfile.iterrows():
                if row["Place_KB_ID"] in refrow["kb_id"].split("|"):
                    return currentfile["kb_id"].unique()[0]
        return row["Place_KB_ID"]

    if systemTable.shape[0] > 0:
        systemTable["Place_KB_ID"] = systemTable.apply(kbidcorrector, axis=1)
    return systemTable


# precision at N
def precisionN(referenceNDCG, systemTable):
    referenceNDCG.rename(columns={"gain": "refGain"}, inplace=True)

    mysystem = (
        systemTable.groupby(["Place_KB_ID", "Type"])[
            "urgent", "unresolved", "current", "gravity", "frame_count"
        ]
        .agg(["sum"])
        .reset_index()
    )
    mysystem.columns = mysystem.columns.droplevel(1)
    if mysystem.shape[0] > 0:
        mysystem = mysystem[mysystem["Place_KB_ID"] != ""]

    merged = pd.merge(
        referenceNDCG[["kb_id", "type", "refGain"]],
        mysystem,
        how="outer",
        left_on=["kb_id", "type"],
        right_on=["Place_KB_ID", "Type"],
    )
    merged.refGain = merged.refGain.fillna(0)
    merged["score"] = merged.apply(lambda x: 1 if x["frame_count"] > 0 else 0, axis=1)
    merged = merged[merged.refGain == int(config["Gain"]["High"])]

    mylist = []
    for my_n in range(1, merged.shape[0] + 1):
        my_n_merged = merged.head(my_n)
        mylist.append(
            (my_n, my_n_merged[my_n_merged.score == True].shape[0] / my_n_merged.shape[0])
        )
    return mylist


def genMAPMAR_results(filename, systemName, referenceTable, systemTable):
    with open(filename, "w") as mapmar_results_file:

        mapmar_results_file.write("SF Diagnostic Scores for Sysyem: " + systemName + "\n")

        mymap, mymar = mapmar(referenceTable, systemTable, genTrue_TypePlace)
        mapmar_results_file.write("EqClass_Type+Place_MAP: " + str(mymap) + "\n")
        mapmar_results_file.write("EqClass_Type+Place_MAR: " + str(mymar) + "\n")

        mymap, mymar = mapmar(referenceTable, systemTable, genTrue_TypePlaceStatus)
        mapmar_results_file.write("EqClass_Type+Place+Status_MAP: " + str(mymap) + "\n")
        mapmar_results_file.write("EqClass_Type+Place+Status_MAR: " + str(mymar) + "\n")

        mymap, mymar = mapmar(referenceTable, systemTable, genTrue_TypePlaceStatusUrgency)
        mapmar_results_file.write("EqClass_Type+Place+Status+Urgency_MAP: " + str(mymap) + "\n")
        mapmar_results_file.write("EqClass_Type+Place+Status+Urgency_MAR: " + str(mymar) + "\n")

        mymap, mymar = mapmar(referenceTable, systemTable, genTrue_TypePlaceStatusResolution)
        mapmar_results_file.write("EqClass_Type+Place+Status+Resolution_MAP: " + str(mymap) + "\n")
        mapmar_results_file.write("EqClass_Type+Place+Status+Resolution_MAR: " + str(mymar) + "\n")

        mymap, mymar = mapmar(referenceTable, systemTable, genTrue_TypePlaceStatusUrgencyResolution)
        mapmar_results_file.write(
            "EqClass_Type+Place+Status+Urgency+Resolution_MAP: " + str(mymap) + "\n"
        )
        mapmar_results_file.write(
            "EqClass_Type+Place+Status+Urgency+Resolution_MAR: " + str(mymar) + "\n"
        )

        referenceGraveTable = referenceTable[
            (referenceTable.urgent == True) & (referenceTable.unresolved == True)
        ]
        systemGraveTable = systemTable[
            (systemTable.urgent == True) & (systemTable.unresolved == True)
        ]
        mymap, mymar = mapmar(
            referenceGraveTable, systemGraveTable, genTrue_TypePlaceStatusUrgencyResolution
        )
        mapmar_results_file.write(
            "GRAVE_EqClass_Type+Place+Status+Urgency+Resolution_MAP: " + str(mymap) + "\n"
        )
        mapmar_results_file.write(
            "GRAVE_EqClass_Type+Place+Status+Urgency+Resolution_MAR: " + str(mymar) + "\n"
        )
    return


def genNDCG_results(filename, systemName, myndcg, k):
    with open(filename, "w") as nDCG_results_file:
        nDCG_results_file.write("SF nDCG Scores for Sysyem: " + systemName + "\n")
        nDCG_results_file.write("k\tnDCG\n")
        for x, y in zip(k, myndcg):
            nDCG_results_file.write("%s\t%s\n" % (x, y))
    return


def genprecisionN_results(filename, systemName, myprecisionN):
    with open(filename, "w") as precisionN_results_file:
        precisionN_results_file.write("SF Precision at N Scores for Sysyem: " + systemName + "\n")
        for x, y in myprecisionN:
            precisionN_results_file.write("%s\t%s\n" % (x, y))
        if len(myprecisionN) == 0:
            precisionN_results_file.write("NOTE: No high gravity situations were found\n")
    return

