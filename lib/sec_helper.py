import numpy as np
import pandas as pd
import glob
import csv


def get_SEC_ref(ref_path): 
    sentiment_files = glob.glob(ref_path + "/sentiments/*.tab")
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
    
    ### THIS IS JUST FOR THE TMP REF 
#     # TODO REMOVE
#     all_sentiments_df['sentiment_value'] = all_sentiments_df['sentiment_value'].map(sentiment_mapping_to_int)
    
    return all_sentiments_df


def preparing_SEC_submission(submission, ref_el, sub_el): 

    # flatten submission
    # first group by 
    subm_grouped = submission[sub_el+["SEC"]].groupby(sub_el)
    list_of_pairs = [[*i,c] for i, b in subm_grouped["SEC"] for a in b.tolist() for c in a]
    # flattening subm sentiments: each SEC element now has a row
    # also renaming the columns to match the ref nameing
    flat = pd.DataFrame(list_of_pairs, columns=ref_el+["sentiments"])
    sentiment_as_series = flat.apply(lambda r: pd.Series(r["sentiments"]), axis=1)
    # setting polarity to match reference naming 
    sentiment_as_series["polarity"] = sentiment_as_series["Sentiment"].apply(lambda x: "positive" if x>0 else "negative")
    # merging back with the full submission info
    subm_sentiments_df = pd.merge(flat, sentiment_as_series, left_index=True, right_index=True).drop(["sentiments"], axis=1)

    #TODO: replace `Source` with mapped NIL ids 
    # implement custom function to replace NIL subm id with reference NIL id
    # subm_sentiments_df["Source"] = ubm_sentiments_df["Source"].map(nil_mapper(edl_ref, edl_sub), na_action='ignore’)

    subm_sentiments_df.set_index(ref_el)
    
    return subm_sentiments_df

def preparing_SEC_reference(reference, sec_ref, ref_el): 
    ref_fields = ref_el + ["frame_id", "kb_id"]
    sec_ref["kb_id_sentiments"] = sec_ref["kb_id"]
    # supplement SEC ref with regular ref information
    ref_sentiments_with_type = pd.merge(
        sec_ref,
        reference, 
        how="left",
        left_on=["doc_id", 'target'],
        right_on=["doc_id", 'frame_id'],
        suffixes=("_sec","_ref")
    )
    ref_sentiments_with_type["kb_id"] = ref_sentiments_with_type["kb_id_ref"]
    ref_sentiments_with_type["emotion_value"] = ref_sentiments_with_type["emotion_value"].str.split(',')
    
    def translate_ref_sentiment(row): 
        if type(row["emotion_value"])== list : 
            return [e in row["emotion_value"] for e in ("anger", "fear", "joyhappiness") ]
        return [False, False, False]

    ref_sentiments_with_type["bool_sentiments"] = ref_sentiments_with_type.apply(translate_ref_sentiment, axis=1)
    ref_sentiments_with_type['Emotion_Anger'],  ref_sentiments_with_type['Emotion_Fear'],ref_sentiments_with_type['Emotion_Joy'] = zip(*ref_sentiments_with_type["bool_sentiments"])

#     ref_sentiments_with_type.set_index(ref_el)
    return  ref_sentiments_with_type 


def matching_frames(row, df, ref_el):
    """For each submission frame, returns all the matching reference frames"""
    
    masks = [df[e]==row[e] for e in ref_el]
    # true mask of right size
    mask  = pd.Series([True for _ in range(0, len(df))]) 
    # make & of all masks 
    for m in masks: 
        mask = mask & m
    
    return df[mask]

def is_sentiment_match(ref, sub): 
    return ref["polarity"]==sub["polarity"] and ref["kb_id_sentiments"] == sub["Source"]

def matching_sentiments(row, inverted=False):
    """default order: row is a reference row, x is a submission row. inverted=True inverts that"""
    def is_sentiment_match_func(x):
        if inverted: 
            return is_sentiment_match(ref=row, sub=x)
        else: 
            return is_sentiment_match(ref=x, sub=row)
    matching_frames = row["matching_frames"]  # this is a dataframe
    filtered_frames = matching_frames.apply(is_sentiment_match_func, axis=1)
    return matching_frames[filtered_frames]


def penalty(row, penalty_factor=.97, matching_key='matching_ref_sentiments'): 
    subm_value = float(row["Sentiment"])
    ref_value = float(row[matching_key].iloc[[0]]["sentiment_value"])
    
    diff = abs(subm_value - ref_value)
    if diff <= 0.5: 
        return 1.
    elif 0.5 < diff <= 1.5:
        return penalty_factor
    else:
        return penalty_factor^2

    
def emotion_matches(row):
    columns = ["Emotion_Anger", "Emotion_Fear", "Emotion_Joy"]
    ref_df = row["matching_ref_sentiments"]
    
    if len(ref_df) == 0: 
        return 0, 3
    
    matched_reference = ref_df.iloc[0][columns]
    
    matches = sum(row[c]==matched_reference[c] for c in columns)
#     matches = sum(row[[columns]] & matched_reference)
    return matches, 3-matches



def SEC_scoring(reference, sec_ref, submission, ref_el=["doc_id", "kb_id", "type"], sub_el=["DocumentID", 'Place_KB_ID', "Type"]):
    ref_sentiments_with_type = preparing_SEC_reference(reference, sec_ref, ref_el)
    subm_sentiments_df = preparing_SEC_submission(submission, ref_el, sub_el)
    
    # from the POV of the submission, get all matching reference FRAMES
    subm_sentiments_df["matching_frames"] = subm_sentiments_df.apply(matching_frames, axis=1, args=(ref_sentiments_with_type, ref_el))
    # from those matching FRAMES, extract the matching SENTIMENTS
    subm_sentiments_df["matching_ref_sentiments"] = subm_sentiments_df.apply(matching_sentiments, axis=1)
    
    # from the POV of the reference, get all matching submission FRAMES
    ref_sentiments_with_type["matching_frames"] = ref_sentiments_with_type.apply(matching_frames, axis=1, args=(subm_sentiments_df, ref_el))
    ref_sentiments_with_type["matching_sub_sentiments"] = ref_sentiments_with_type.apply(matching_sentiments, axis=1, args=(True,))
    
    matches = subm_sentiments_df["matching_ref_sentiments"].apply(lambda x: len(x))
    single_matches = matches[matches==1]

    # all the SEC groups that match at least one reference are a TP 
    tp_matches = matches[matches>=1]   
    tp = len(tp_matches)
    # all the SEC groups that match 0 reference are a FP 
    fp = len(matches[matches==0])   
    # from the ref POV, all the ref SEC groups that match 0 submission are a FN
    ref_matches = ref_sentiments_with_type["matching_sub_sentiments"].apply(lambda x: len(x))
    fn = len(ref_matches) - len(ref_matches[ref_matches>=1])

    PrecisionPolarity = tp/(tp+fp)
    RecallPolarity = tp/(tp+fn)
    try:
        F1Polarity = 2*PrecisionPolarity*RecallPolarity/(PrecisionPolarity+RecallPolarity)
    except ZeroDivisionError: 
        F1Polarity = np.NAN 
    
    # SENTIMENT VALUE SECTION 
    
    # penalized TP 
    penalized_tp = subm_sentiments_df[matches>=1].apply(penalty, axis=1, result_type='reduce')
    total_penalty = sum(penalized_tp)
    
    PrecisionSentiment = total_penalty/(tp+fp)
    RecallSentiment = total_penalty/(tp+fn)
    try: 
        F1Sentiment = 2*PrecisionSentiment*RecallSentiment/(PrecisionSentiment+RecallSentiment)
    except ZeroDivisionError: 
        F1Sentiment = np.NAN 
    
    ## EMOTION SECTION 
    
    matches, non_matches =  zip(*subm_sentiments_df.apply(emotion_matches, axis=1))

    PrecisionEmotion = sum(matches)/(3*len(subm_sentiments_df))
    RecallEmotion = sum(matches)/(3*len(ref_sentiments_with_type))
    try: 
        F1Emotion = 2*PrecisionEmotion*RecallEmotion/(PrecisionEmotion+RecallEmotion)
    except ZeroDivisionError: 
        F1Emotion = np.NAN 

    PrecisionEmotion, RecallEmotion, F1Emotion
    
    #TODO the last metric, returning NAN for now
    return PrecisionPolarity, RecallPolarity, F1Polarity, PrecisionSentiment, RecallSentiment, F1Sentiment, PrecisionEmotion, RecallEmotion, F1Emotion

