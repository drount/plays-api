# -*- coding: utf-8 -*-
from collections import defaultdict

"""
Best Position Algorithms for Top-k queries

All algorithms expect a database m consisting of a dictionary of items with 
scores. 

E.g.
m = {
    "list1": {"item1": 10, "item2": 6, "item3": 3},
    "list2": {"item4": 15, "item1": 2},
}
"""

def fa(m, k):
    """
    Fagin's Algorithm from paper: 
    Combining fuzzy information from multiple systems
    by R.Fagin
    """
    
    sorted_lists = _get_sorted_lists(m)
    
    def item_dict():
        return {
            'score': 0,
            'lists': []
        }
    
    # Sorted access
    # Access in parallel to each of the sorted lists
    # Maintain each seen item in a set until there are at least k data items
    # that have been seen in all lists
    items = defaultdict(item_dict)
    
    i = 0
    common_items = 0
    list_count = len(sorted_lists)
    max_list_size = max([len(l) for l in sorted_lists.values()])
    
    stop = False
    while not stop:
        for l_key, l_value in sorted_lists.items():
            if i < len(l_value):
                item, score  = l_value[i]
                items[item]['score'] += score
                items[item]['lists'].append(l_key)
                 
                if len(items[item]['lists']) == list_count:
                    common_items += 1
                
        i += 1
        if common_items >= k or i >= max_list_size:
            stop = True
    
    # Random Access
    # For each data item in s, do a random access to all the lists wher it has
    # not been seen, and update the score
    for key, value in items.items():
        if len(value['lists']) == list_count:
            continue
    
        unvisited_lists = set(sorted_lists.keys()).difference(set(value['lists']))
        for unvisited in unvisited_lists:
            # Update score if item is present in the unvisited list
            if key in m[unvisited]:
                items[key]['score'] += m[unvisited][key]
    
    
    # Sort by descending and slice top k
    top_k_items = [(key, value['score']) for key, value in items.items()]
    top_k_items = sorted(top_k_items, key=lambda x: -x[1])
    return top_k_items[:k]


def ta(m, k):
    """
    Threshold Algorithm
    """
    raise NotImplementedError


def bpa(m, k):
    """
    Best Position Algorithm
    """
    raise NotImplementedError


def bpa2(m, k):
    """
    Best Position Algorithm Optimization
    """
    raise NotImplementedError


def _get_sorted_lists(m):
    """
    Converts the elements of the database into sorted lists by descending score
    """
    sorted_lists = {}
    for l_key, l_value in m.items():
        s = []
        for key, value in l_value.items():
            s.append((key, value))
        sorted_lists[l_key] = sorted(s, key=lambda x: -x[1])
    return sorted_lists