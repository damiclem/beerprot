import json
import argparse
import requests
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from tqdm import tqdm

def get_statistics(df):
    stats = {}
    for column in df.columns[-4:]:
        sequences_with_domain = df.groupby(column)['SP_PRIMARY'] \
            .unique().apply(lambda x: len(x)).sort_values(ascending=False)
        stats[column] = sequences_with_domain
    return stats


if __name__ == '__main__':

    # 1. Define arguments
    parser = argparse.ArgumentParser()
    ### Path of the files
    parser.add_argument('--pdb_to_uniprot_path',  type=str,   default='data/pdb/pdb_chain_uniprot.tsv')
    parser.add_argument('--pdb_to_cath_path',     type=str,   default='data/pdb/pdb_chain_cath_uniprot.tsv')
    parser.add_argument('--original_path',        type=str,   default='data/results/jackhmmer.tsv')

    # 2. Define dictionary of args
    args = parser.parse_args()

    # 3. Load files
    original = pd.read_csv(args.original_path, sep='\t', dtype=str)
    pdb_cath = pd.read_csv(args.pdb_to_cath_path, sep ='\t', header=1, dtype=str)
    pdb_uniprot = pd.read_csv(args.pdb_to_uniprot_path, sep ='\t', header=1, dtype=str)

    # 4. Slice CATH
    pdb_cath = pdb_cath[pdb_cath.SP_PRIMARY.isin(original.entry_ac)]

    # 5. Download data of CATH

    url = 'http://www.cathdb.info/version/v4_1_0/api/rest/domain_summary'
    cath_superfamily = []
    cath_ids = pdb_cath.CATH_ID.tolist()
    batch_size = 50
    delay = 3

    print('Starting queries. Total queries: {}'.format(len(cath_ids)))
    for i in range(0, len(cath_ids), batch_size):
        # Define batch ids
        batch_ids = cath_ids[i:min(len(cath_ids), i + batch_size)]
        for cath_id in tqdm(batch_ids):
            res = requests.get('/'.join([url, cath_id]), headers={'Accept': 'application/json'})
            if res.status_code == 400:
                cath_superfamily.append(None)
                continue
            res_dict = res.json()
            cath_superfamily.append(res_dict['data']['superfamily_id'])
        time.sleep(delay)

    # 6. Create final dataset
    ### ADD RESULTS ON PDB_CATH
    pdb_cath['CATH'] = cath_superfamily
    db_uniprot = pdb_uniprot[pdb_uniprot.SP_PRIMARY.isin(original.entry_ac)]
    pdb_uniprot = pdb_uniprot.merge(pdb_cath[['PDB', 'CATH_ID', 'CATH']], how='left', on='PDB')

    ### Parse CATH values
    cath = pdb_uniprot.groupby(by = ['SP_PRIMARY', 'CATH']).size().reset_index(name='counts')
    cath = cath.sort_values(by='SP_PRIMARY')

    C, A, T, H = [], [], [], []
    for cath_value in cath.CATH:
        c, a, t, h = cath_value.split('.')
        C.append(c)
        A.append('.'.join([c,a]))
        T.append('.'.join([c,a,t]))
        H.append('.'.join([c,a,t,h]))
    cath['Class'] = C
    cath['Architecture'] = A
    cath['Topology'] = T
    cath['Homologous'] = H
    cath.head()

    stat_superfamily = get_statistics(cath)
    # 7. Show results
    fig, ax = plt.subplots(2, 2, figsize=(18, 14))

    C = stat_superfamily['Class']
    ax[0, 0].bar(sorted(C.keys()), height=C.values)
    ax[0, 0].set_xlabel('Class')
    ax[0, 0].set_ylabel('Frequencies')
    ax[0, 0].set_title('Class Distribution')
    ax[0, 0].set_xticklabels(['Mainly Alpha', 'Mainly Beta', 'Alpha Beta'], rotation=0)
    ax[0, 0].grid()
    # A
    A = stat_superfamily['Architecture']
    ax[0, 1].bar(sorted(A.keys()), height=A.values)
    ax[0, 1].set_xlabel('Architecture')
    ax[0, 1].set_ylabel('Frequencies')
    ax[0, 1].set_title('Architecture Distribution')
    ax[0, 1].grid()
    # T
    T = stat_superfamily['Topology']
    ax[1, 0].bar(sorted(T.keys()), height=T.values)
    ax[1, 0].set_xlabel('Topology')
    ax[1, 0].set_ylabel('Frequencies')
    ax[1, 0].set_title('Topology Distribution')
    ax[1, 0].set_xticklabels(sorted(T.keys()), rotation=90)
    ax[1, 0].grid()
    # H
    S = stat_superfamily['Homologous']
    ax[1, 1].bar(sorted(S.keys()), height=S.values)
    ax[1, 1].set_xlabel('Homologous')
    ax[1, 1].set_ylabel('Frequencies')
    ax[1, 1].set_title('Superfamily Distribution')
    ax[1, 1].set_xticklabels(sorted(S.keys()), rotation=90)
    ax[1, 1].grid()

    print(cath)
    plt.show()
