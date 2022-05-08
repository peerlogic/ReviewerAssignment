from flask import Flask, request, render_template, redirect
import random
import flask
import numpy
from random import randint

app = Flask(__name__)

list_subsets = []

def reviewer_subset_with_sum(sublist, needed_sublist_len, expected_sum, n_submission):
    if needed_sublist_len == len(sublist):
        if not sublist in list_subsets:
            if abs(sum([r['reputation'] for r in sublist])-expected_sum)<0.5:
                list_subsets.append(sublist)
                return list_subsets
    if len(sublist) > needed_sublist_len:
        for i in sublist:
            aux = sublist[:]
            aux.remove(i)
            reviewer_subset_with_sum(aux, needed_sublist_len, expected_sum, n_submission)

def assign_reviews_dist_reputation(submissions, reviewers, n_max_reviewer):

    submission_reviewers_map = {}
    reviewers_task_map = {}
    n_reviewer = len(reviewers)

    #find the median of reputations
    reputations = [float(r['reputation']) for r in reviewers]
    data = numpy.array(reputations)
    median = numpy.median(data)
    expected_sum = median * n_max_reviewer

    #sort reviewers based on their reputation
    sorted_reviewers = sorted(reviewers, key=lambda k: k['reputation'])

    #for each submission find random n reviewers whose sum of reputations approx eq to expected_sum
    for submission in submissions:
        #divide the reviewers into n_max_reviewer groups
        n_each_reviewer_block = len(reviewers) / n_max_reviewer
        reputation_sum = 0
        reviewer_team = []
        skipped = 0
        for i in range(0, n_max_reviewer+1):
            reviewer_index = 0
            # take a random reviewer from each block
            start_block = i * n_each_reviewer_block
            # put the reminder in the last block
            end_block = i * n_each_reviewer_block + n_each_reviewer_block - 1 if i <  n_max_reviewer-1 else len(reviewers) - 1

            #check if all reviewers in this block are in conflict, then we have to skipped this block
            if set([r['reviewer_id'] for r in sorted_reviewers[start_block:end_block+1]]) < set(submission['conflicts']):
                skipped += 1
                continue

            #this iteration is not skipped, but we have to assign reviewers for this one as well as for the skipped iterations
            for j in range(-1, skipped):
                while True:
                    reviewer_index = randint(start_block, end_block)
                    reputation_sum += float(sorted_reviewers[reviewer_index]['reputation'])
                    if not sorted_reviewers[reviewer_index]['reviewer_id'] in submission['conflicts']:
                        if i < n_max_reviewer:
                            break
                        elif i == n_max_reviewer and abs(reputation_sum-expected_sum) < (1/10 * expected_sum):
                            break
                    reputation_sum -= float(sorted_reviewers[reviewer_index]['reputation'])

                reviewer_team.append(sorted_reviewers[reviewer_index])

                if not sorted_reviewers[reviewer_index]['reviewer_id'] in reviewers_task_map.keys():
                    reviewers_task_map[sorted_reviewers[reviewer_index]['reviewer_id']] = []
                reviewers_task_map[sorted_reviewers[reviewer_index]['reviewer_id']].append(submission)

        submission_reviewers_map[submission['submission_id']] = reviewer_team


    #find subsets of reviewers with the length of n_max_reviewer
    #reviewer_subset_with_sum(reviewers, n_max_reviewer, expected_sum)
    #reviewer_combinations = list_subsets

    # reviewer_team_index = 0

    # for submission in submissions:
    #     while True:
    #         if not set([r['reviewer_id'] for r in reviewer_combinations[reviewer_team_index]]).issubset(submission['conflicts']):
    #             submission_reviewers_map[submission['submission_id']] = reviewer_combinations[reviewer_team_index]
    #             #TODO update each reviewer's task
    #             reviewer_team_index = (reviewer_team_index + 1) % len(reviewer_combinations)
    #             break


    return flask.jsonify(submissions=submission_reviewers_map, tasks=reviewers_task_map)

def assign_reviews_random(submissions, reviewers, n_max_reviewer):
    submission_reviewers_map = {}
    reviewers_task_map = {}
    n_reviewer = len(reviewers)

    if n_max_reviewer < n_reviewer:
        random.shuffle(reviewers)

        reviewer_index = -1
        for i in range(0, n_max_reviewer):
            for j in range(0, len(submissions)):

                while True:
                    reviewer_index = (reviewer_index + 1) % n_reviewer
                    if reviewers[reviewer_index]['reviewer_id'] in submissions[j]['conflicts']:
                        print 'skip conflict'
                    elif submissions[j]['submission_id'] in submission_reviewers_map.keys() and \
                                    reviewers[reviewer_index] in submission_reviewers_map[submissions[j]['submission_id']]:
                        print 'skip redundant'
                    #elif not submissions[j]['submission_id'] in submission_reviewers_map.keys():
                    #    break
                    else:
                        break


                if submissions[j]['submission_id'] in submission_reviewers_map.keys():
                    submission_reviewers_map[submissions[j]['submission_id']].append(reviewers[reviewer_index])
                else:
                    submission_reviewers_map[submissions[j]['submission_id']] = [reviewers[reviewer_index]]

                if reviewers[reviewer_index]['reviewer_id'] in reviewers_task_map.keys():
                    reviewers_task_map[reviewers[reviewer_index]['reviewer_id']].append(submissions[j])
                else:
                     reviewers_task_map[reviewers[reviewer_index]['reviewer_id']] = [submissions[j]]


    else:
        raise ValueError('number of reviews per submission must be smaller than number of reviewers')


    return flask.jsonify(submissions=submission_reviewers_map, tasks=reviewers_task_map)

def assign_reviews_preference(submissions, reviewers, n_max_reviewer):
    submission_reviewers_map = {}
    reviewers_task_map = {}
    n_reviewer = len(reviewers)

    if n_max_reviewer < n_reviewer:
        random.shuffle(reviewers)


        #distribute reviewers based on their preferences
        for j in range(0, len(submissions)):
            #sequentially find reviewers with preference reviewing this article
            reviewer_index = -1
            reviewer_team = []

            while len(reviewer_team) < n_max_reviewer and reviewer_index < n_reviewer - 1:
                reviewer_index = (reviewer_index + 1)

                reviewer_team = submission_reviewers_map.get(submissions[j]['submission_id'])
                reviewer_team = [] if reviewer_team == None else reviewer_team

                if not submissions[j]['submission_id'] in reviewers[reviewer_index]['preferences']:
                    continue
                elif reviewers[reviewer_index]['reviewer_id'] in submissions[j]['conflicts'] :
                    continue
                #move on if he's already a reviewer for this submission
                elif reviewers[reviewer_index] in reviewer_team:
                    continue

                reviewer_team.append(reviewers[reviewer_index])

                this_reviewer_tasks = reviewers_task_map.get(reviewers[reviewer_index]['reviewer_id'])
                this_reviewer_tasks = [] if this_reviewer_tasks == None else this_reviewer_tasks
                this_reviewer_tasks.append(submissions[j])

                reviewers_task_map[reviewers[reviewer_index]['reviewer_id']] = this_reviewer_tasks

                submission_reviewers_map[submissions[j]['submission_id']] = reviewer_team

        #calculate the avg utilization of each reviewer
        n_avg_task_reviewer = 0
        for tasks in reviewers_task_map.values():
            n_avg_task_reviewer = n_avg_task_reviewer + len(tasks)
        n_avg_task_reviewer = n_avg_task_reviewer/float(len(reviewers_task_map.values()))

        #now distribute the rest of the reviewers to the submission with reviewers less than max_n_review
        for j in range(0, len(submissions)):
            reviewer_index = -1
            reviewer_team = []
            while len(reviewer_team) < n_max_reviewer:
                reviewer_index = (reviewer_index + 1) % n_reviewer

                #check the workload of this reviewer
                this_reviewer_tasks = reviewers_task_map.get(reviewers[reviewer_index]['reviewer_id'])
                this_reviewer_tasks = [] if this_reviewer_tasks == None else this_reviewer_tasks

                #move on if he's already over utilized
                if len (this_reviewer_tasks) > n_avg_task_reviewer:
                    continue
                #move on if he's already a reviewer for this submission
                elif reviewers[reviewer_index] in reviewer_team:
                    continue
                #move on if he's in the conflict list
                elif reviewers[reviewer_index]['reviewer_id'] in submissions[j]['conflicts']:
                    continue

                reviewer_team = submission_reviewers_map.get(submissions[j]['submission_id'])
                reviewer_team = [] if reviewer_team == None else reviewer_team

                reviewer_team.append(reviewers[reviewer_index])
                submission_reviewers_map[submissions[j]['submission_id']] = reviewer_team

                this_reviewer_tasks.append(submissions[j])
                reviewers_task_map[reviewers[reviewer_index]['reviewer_id']] = this_reviewer_tasks



                n_avg_task_reviewer = n_avg_task_reviewer + 1/float(len(reviewers))

    else:
        raise ValueError('number of reviews per submission must be smaller than number of reviewers')


    return flask.jsonify(reviews=submission_reviewers_map, tasks=reviewers_task_map)


@app.route('/sample/<algorithm>', methods=['GET', 'POST'])
def assign_algorithm_sample_data(algorithm):
    if request.method == 'GET':
        submissions = [{'submission_id':'S00', 'conflicts':['R01']},
                       {'submission_id':'S01', 'conflicts':['R02']},
                       {'submission_id':'S02', 'conflicts':['R04']},
                       {'submission_id':'S03', 'conflicts':['R06']},
                       {'submission_id':'S04', 'conflicts':['R08']}]

        reviewers = [{'reviewer_id':'R00', 'name':'Donald Trump', 'reputation':0.5, 'preferences':['S00', 'S01']},
                     {'reviewer_id':'R01', 'name':'Hilary Clinton', 'reputation':0.75, 'preferences':['S01', 'S02']},
                     {'reviewer_id':'R02', 'name':'Bart Simpson', 'reputation':0.5, 'preferences':['S02', 'S03']},
                     {'reviewer_id':'R03', 'name':'Mickey Mouse', 'reputation':0.4, 'preferences':['S01']},
                     {'reviewer_id':'R04', 'name':'Minie Mouse', 'reputation':0.8, 'preferences':['S02']},
                     {'reviewer_id':'R05', 'name':'Oliver Quenn', 'reputation':0.3, 'preferences':['S02']},
                     {'reviewer_id':'R06', 'name':'Clark Kent', 'reputation':0.5, 'preferences':['S03']},
                     {'reviewer_id':'R07', 'name':'Bruce Wayne', 'reputation':0.7, 'preferences':['S03']},
                     {'reviewer_id':'R08', 'name':'Louise Lane', 'reputation':0.5, 'preferences':['S04']},
                     {'reviewer_id':'R09', 'name':'Lana Lang', 'reputation':0.9, 'preferences':['S04']},
                     {'reviewer_id':'R10', 'name':'Gina Jane', 'reputation':0.5, 'preferences':['S04']},
                     {'reviewer_id':'R11', 'name':'Joe Binden', 'reputation':0.9, 'preferences':['S04']}]

        n_max_reviewer = 4
    else:
        data = request.json
        submissions = data['submissions']
        reviewers = data['reviewers']
        n_max_reviewer = data['n_max_reviewer']

    if algorithm == 'random':
        assignment = assign_reviews_random(submissions, reviewers, n_max_reviewer)
    elif algorithm == 'preference':
        assignment = assign_reviews_preference(submissions, reviewers, n_max_reviewer)
    elif algorithm == 'reputation':
        assignment = assign_reviews_dist_reputation(submissions, reviewers, n_max_reviewer)
    else:
        return flask.jsonify(error="supported algorithms are 'random', 'preference', 'reputation'.")
    #assign_reviews_preference(submissions, reviewers, n_max_reviewer)
    #assignment = assign_reviews_random(submissions, reviewers, 6)

    return assignment


@app.route('/', methods=['GET'])
def index():
    return redirect("/random", code=302)


@app.route('/<algorithm>', methods=['GET', 'POST'])
def assign_algorithm(algorithm):
    if request.method == 'GET':
        return render_template("index.html")
    else:
        data = request.json
        submissions = data['submissions']
        reviewers = data['reviewers']
        n_max_reviewer = data['n_max_reviewer']


    if algorithm == 'random':
        assignment = assign_reviews_random(submissions, reviewers, n_max_reviewer)
    elif algorithm == 'preference':
        assignment = assign_reviews_preference(submissions, reviewers, n_max_reviewer)
    elif algorithm == 'reputation':
        assignment = assign_reviews_dist_reputation(submissions, reviewers, n_max_reviewer)
    else:
        return flask.jsonify(error="supported algorithms are 'random', 'preference', 'reputation'.")

    return assignment

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3007, threaded=True)


