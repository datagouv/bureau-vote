import pandas as pd
from difflib import SequenceMatcher
import re

def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Put fields of strings in lowercase and remove the names of persons from the dataset

    Args:
        df (pd.DataFrame): the raw dataframe read from INSEE file

    Returns:
        pd.DataFrame: a dataframe without any names, where some column names and column content have been normalized
    """
    df = df.rename(columns={
        'Numéro de voie': 'num_voie',
        'Type et libellé de voie': 'libelle_voie',
        'Complément d’adresse 1': 'comp_adr_1',
        'Complément d’adresse 2': 'comp_adr_2',
        'Lieu-dit  ': 'lieu-dit',
        'Code commune\nRéférentiel': 'Code communeRéférentiel',
        'Libellé commune\nRéférentiel': 'Libellé communeRéférentiel'
    })
    df['num_voie'] = df['num_voie'].str.lower()
    df['libelle_voie'] = df['libelle_voie'].str.lower()
    df['comp_adr_1'] = df['comp_adr_1'].str.lower()
    df['comp_adr_2'] = df['comp_adr_2'].str.lower()
    df['lieu-dit'] = df['lieu-dit'].str.lower()
    

    df['num_voie_clean'] = df['num_voie'].apply(
        lambda x: remove_names(str(x))
    )
    df['libelle_voie_clean'] = df['libelle_voie'].apply(
        lambda x: remove_names(str(x))
    )
    df['comp_adr_1_clean'] = df['comp_adr_1'].apply(
        lambda x: remove_names(str(x))
    )
    df['comp_adr_2_clean'] = df['comp_adr_2'].apply(
        lambda x: remove_names(str(x))
    )
    df['lieu-dit-clean'] = df['lieu-dit'].apply(
        lambda x: remove_names(str(x))
    )
    df['adr_complete'] = df.apply(lambda row: get_address(row),axis=1)
    return df


def remove_names(x: str) -> str:
    """
    This function is specific to the Ariege dataset. It normalizes text, detect the presence of the word "chez" and remove the names following this word.
    In particular the function assumes that:
        (i) the names of a person is made of 2 tokens (composed-words count for one), and can possibly follow tokens like "m."/"madame"...
        (ii) there is at most 2 persons mentioned in one field, and the two names are then only separated with the word "et"

    Args:
        x (str): a string  possibly containing names, following the conditions above

    Returns:
        str: a string where names have been removed
    """
    x = x.replace('(','').replace(')','').replace('.','').replace(',','').replace(';','').replace('/','').lower()
    if('chez' in x):
        adr = x.split('chez')[0]
        chez = x.split('chez')[1]
        to_parse = chez.split(' ')
        if(len(to_parse) > 1):
            if(to_parse[1] in ['m.', 'm', 'mr', 'mme', 'mlle', 'monsieur', 'madame', 'mademoiselle']):
                if(len(to_parse) > 4):
                    if(to_parse[4] == 'et'):
                        if(len(to_parse) > 5 and to_parse[5] in ['m.', 'm', 'mr', 'mme', 'mlle', 'monsieur', 'madame', 'mademoiselle']):
                            adr = adr + ' '.join(to_parse[8:])
                        else:
                            adr = adr + ' '.join(to_parse[7:])
                    else:
                        adr = adr + ' '.join(to_parse[4:])
            else:
                if(len(to_parse) > 3):
                    if(to_parse[3] == 'et'):
                        adr = adr + ' '.join(to_parse[4:])
                    else:
                        adr = adr + ' '.join(to_parse[3:])
        if adr == 'nan':
            return ''
        else:
            return adr
    else:
        if x == 'nan':
            return ''
        else:
            return x
        
        
def clean_geocoded_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean some types of the dataframe after the geocoding step
    """
    geocoded_df = df.copy()
    geocoded_df["latitude"] = geocoded_df["latitude"].astype(float)
    geocoded_df["longitude"] = geocoded_df["longitude"].astype(float)
    geocoded_df["result_score"] = geocoded_df["result_score"].astype(float)
    geocoded_df = geocoded_df[geocoded_df["result_label"].notna()]
    return geocoded_df

            
def clean_failed_geocoding(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove both failed geocoding (geocoding score below a threshold) + also remove lines where the voter does not inhabit in the same code commune + also remove lines where the geocoding is not consistent with the postcode indicated in the INSEE file

    Args:
        df (pd.DataFrame): a dataframe where geocoding has already been performed with API-adresse

    Returns:
        pd.DataFrame: a cleaned subset of this dataframe
    """
    assert "result_score" in df.columns and "result_postcode" in df.columns and "CP" in df.columns and "CP_BV" in df.columns and "result_citycode" in df.columns and "Code communeRéférentiel" in df.columns, "the dataframe does not include required columns for cleaning"
    # the comparison is performed on column "result_postcode" (because there is no citycode in INSEE input file) but other functions will only refer to "result_citycode" (because it is a good practice to prefer this column)
    return df[(df.result_score > 0.5) & (df.result_citycode == df["Code communeRéférentiel"]) & (df.result_postcode == df.CP)].dropna(subset=["CP", "result_citycode", "result_postcode"])


def get_address(row) -> str:
    """
    Build a unique address string by combining several fields

    Args:
        row : a row of pd.DataFrame

    Returns:
        str: the address
    """
    def similar(a: str, b: str): # return a measure of similarity
        return SequenceMatcher(None, a, b).ratio()
    address = str(row['num_voie_clean']) + ' ' + \
    str(row['libelle_voie_clean']) + ' ' + str(row['comp_adr_1_clean']) + ' ' + str(row['comp_adr_2_clean'])

    if((similar(str(address), str(row['lieu-dit-clean']).lower()) > 0.7) | (str(row['lieu-dit-clean']).lower() == 'nan')):
        return str(address)
    else:
        return str(address) + ' ' + str(row['lieu-dit-clean']).lower()
    
    
def prepare_ids(df:pd.DataFrame) -> pd.DataFrame:
    """
    Prepare `id_bv` (integers) column
    
    Args:
        df (pd.DataFrame): a dataframe including columns "Code_BV" and "result_citycode"

    Returns:
        pd.DataFrame: a dataframe similar to the input, with a supplementary column "id_bv" (integers) unique for every bureau de vote
    """
    assert ("Code_BV" in df.columns) and ("result_citycode" in df.columns), "There is no identifiers for bureau de vote"
    df_copy = df.copy()
    def prepare_id_bv(row):
        """
        Combine the unique id of a city (citycode) and the number of the bureau de vote inside the city to compute a nationalwide id of bureau de vote

        Args:
            row (_type_): _description_

        Returns:
            id_bv: integer serving as unique id of a bureau de vote
        """
        max_bv_per_city = 1000 # assuming there is always less than this number of bv in a city. This is important to grant the uniqueness of id_bv
        max_code_commune = 10**5
        try:
            code_bv = int(row["Code_BV"])
        except:
            # keep as Code_BV the first number found in the string (if there is one)
            found = re.search(r'\d+', row["Code_BV"])
            if found:
                code_bv = int(found.group())
            else:
                code_bv = max_bv_per_city # this code will indicate parsing errors but won't raise exception
        try:
            code_commune = int(row['result_citycode'])
        except:
            found = re.search(r'\d+', row["result_citycode"])
            if found:
                code_commune = int(found.group())
            else:
                code_commune = max_code_commune
        return max_bv_per_city*code_commune + code_bv

    df_copy["id_bv"] = df_copy.apply(prepare_id_bv, axis=1)
    return df_copy
    
    