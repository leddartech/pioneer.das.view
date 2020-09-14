
from pioneer.das.api import platform
from pioneer.das.api.datasources import VirtualDatasource

import argparse
import matplotlib.pyplot as plt
import numpy as np

def timestamp_shifting(sync, reference):
    shifts = {}
    ref_ts = sync.platform[reference].timestamps[sync.sync_indices[:,sync.sync_labels.index(reference)]].astype('f8')
    for datasource in sync.sync_labels:
        if reference == datasource:
            continue
        if isinstance(sync.platform[datasource], VirtualDatasource):
            continue
        ds_ts = sync.platform[datasource].timestamps[sync.sync_indices[:,sync.sync_labels.index(datasource)]].astype('f8')
        shifts[f'{datasource} - {reference}'] = (ds_ts - ref_ts)
    return shifts


def check_synchronization(pf, sync_labels=[], min_tol_us=1e2, max_tol_us=1e4, nb_checks:int=10, plot:bool=True):
    """
    Checks how many synchronized frames are found for some values of tolerance.
    Then, if plot is True, shows the timestamps difference between all combinations of datasources
    """

    if len(sync_labels) == 0:
        from das.api.viewer import DEFAULT_SYNC_LABELS
        sync_labels = DEFAULT_SYNC_LABELS

    tolerances = np.logspace(np.log10(min_tol_us),np.log10(max_tol_us),nb_checks)
    lens = []

    for tol in tolerances:
        sync = pf.synchronized(sync_labels, [], tol)
        lens.append(len(sync))
        print(f'{lens[-1]} synchronized frames with a {tol/1e3:.1f} ms tolerance.')

    if plot:
        fig = plt.figure(figsize=(6,2*len(sync.keys())))
        sync = pf.synchronized(sync_labels, [], max_tol_us)
        for i, reference in enumerate(sync.keys()):
            if isinstance(pf[ds], VirtualDatasource):
                continue
            ax = fig.add_subplot(len(sync.keys()),1,i+1)
            shifts = timestamp_shifting(sync, reference)
            for datasource in sync.keys():
                if reference == datasource:
                    continue
                ax.plot(shifts[f'{datasource} - {reference}'], label=f'{datasource} - {reference}')
            ax.set_ylabel('Error [us]')
            ax.legend()
        plt.show()

        
    return tolerances, lens


if __name__ == "__main__":

    argparser = argparse.ArgumentParser()
    argparser.add_argument('-d','--dataset')
    argparser.add_argument('-s','--sync_labels', type=list, default=[])
    argparser.add_argument('-min','--min_tol_us', type=float, default=1e2)
    argparser.add_argument('-max','--max_tol_us', type=float, default=1e4)
    argparser.add_argument('-n','--nb_checks', type=int, default=10)
    argparser.add_argument('-p','--plot', type=bool, default=True)
    args = argparser.parse_args()

    pf = platform.Platform(args.dataset, ignore=['radarTI_bfc'], progress_bar=False)
    check_synchronization(pf, 
        sync_labels=args.sync_labels, 
        min_tol_us=args.min_tol_us, 
        max_tol_us=args.max_tol_us, 
        nb_checks=args.nb_checks, 
        plot=args.plot)
