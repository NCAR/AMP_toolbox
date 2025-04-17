#!/usr/bin/env python3

#import needed python modules:
import argparse
import sys
from getpass import getpass
from zoneinfo import ZoneInfo

#This script uses the Non-standard
#"PyGithub" package, which is
#described here:
#https://pygithub.readthedocs.io/en/stable/introduction.html

#Import needed PyGithub modules:
from github import Github
from github import Auth
from github import BadCredentialsException

###########################
# Helper functions
###########################

def parse_command_line(args, description):

    """
    Parses command-line input arguments
    using the argparse python module and
    outputs the final argument object.
    """

    #Create description:
    desc = "Collect and print your Github statistics for"
    desc += "a given repository.  Currently this only"
    desc += "includes pull request reviews."

    #Create parser object:
    parser = argparse.ArgumentParser(description=desc)

    #Add input arguments to be parsed:
    #----

    helpstr = "The name of the org/repo"
    helpstr += " (must always include both with a '/' delimiter)."

    parser.add_argument('-r', '--repository',
                        metavar='<organization/repository>',
                        action='store', type=str,
                        required=True, help=helpstr)

    #----

    helpstr = "Start date (year and month) from which to begin"
    helpstr += " collecting stats.  Currently ends at present date."

    parser.add_argument('-sd', '--start-date',
                        metavar='<YYYYMM>',
                        action='store', type=str,
                        required=True, help=helpstr)

    #----

    helpstr = "Github user to collect stats for"
    helpstr += " (defaults to logged-in user)."

    parser.add_argument('-u', '--username',
                        metavar='<username>',
                        action='store', type=str,
                        help=helpstr)

   #----

    #Parse Argument inputs:
    args = parser.parse_args()

    #Check that repo string contains a "/"
    #delimiter:
    assert "/" in args.repository, "repository argument must be '<org>/<repo>'"

    #Return arguments object:
    return args

###########################
# Main script
###########################

def main_script():

    """
    Main script that runs/manages all
    functionality for this program.
    """

    #Script requires python version 3.9 or greater,
    #so throw an error if not the case:
    if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 9):
        emsg = "This script requires python 3.9 or later, currently using python version"
        emsg += f" {sys.version_info[0]}.{sys.version_info[1]}"
        raise SystemError(emsg)
    #End if

    #Parse command line arguments:
    args = parse_command_line(sys.argv[1:], __doc__)

    #Extract org and repo strings from input arg:
    repo_args = args.repository.rsplit("/")

    #Extract year and month:
    start_year  = int(args.start_date[0:4])
    start_month = int(args.start_date[5:])

    #Get Github Authentication token:
    token_val = getpass(prompt='Auth. Token:')

    #Create Authentication object:
    token_auth = Auth.Token(token_val)

    #Create Github object
    ghub = Github(auth=token_auth)

    #Try and get user login:
    try:
        username = ghub.get_user().login
    except BadCredentialsException:
        #Raise a new error to make it clear what the
        #problem is (as the normal traceback can be
        #a little confusing):
        raise ValueError("Bad Github authorization token!")
    #End try/except

    #Set Github username,
    #if username not provided,
    #then assume same name as login:
    if  args.username:
        username = args.username
    #End if

    #Extract requested organization:
    org = ghub.get_organization(repo_args[0])

    #Extract requested repo:
    repo = org.get_repo(repo_args[1])

    #Extract pull requests:
    #Note:  PRs are ordered by their creation date,
    #starting with newest PR.
    pulls = repo.get_pulls(state='all')

    #Set timezone (currently assumed to be Denver):
    denver_time = ZoneInfo("America/Denver")

    #Set review counters:
    num_reviewed_prs = 0  #Number of PRs reviewed
    num_additions    = 0  #Number of lines where code was added
    num_deletions    = 0  #Number of lines where code was deleted

    #Set review max values:
    max_pr_additions = 0  #Maximum number of additions for a single PR
    max_pr_num       = 0  #PR number which contained maximum number of adds

    #Set creation counters:
    num_created_prs = 0   #Number of PRs created
    num_create_adds = 0   #Number of lines where code was added
    num_create_dels = 0   #Number of lines where code was deleted

    #Set creation max values:
    max_created_pr_adds = 0 #Maximum number of additions for a single created PR
    max_created_pr_num  = 0 #created PR number which contained maximum of adds

    #Notify user that PR loop has started:
    print(f"Looping over PRs for {repo_args[0]}/{repo_args[1]}...")

    #Set loop break variable:
    stop_loop = False

    #Loop over pull requests:
    for pr in pulls:

        #First check if the PR loop should be stopped:
        if(stop_loop):
            break
        #End if

        #Next check that the PR wasn't merged before the start date,
        #if so then end PR loop:
        if pr.merged:
            merge_date = pr.merged_at.astimezone(denver_time)
            if (merge_date.year < start_year) or \
                (merge_date.year == start_year and \
                merge_date.month < start_month):
                break
            #End if
        #End if

        print(f"On PR number {pr.number}")

        #check if user created the PR,
        #if so then collect PR creation stats:
        created_pr = False
        if pr.user.login == username:
            created_pr = True
            #Add one to PRs created counter:
            num_created_prs += 1
            #Add number of lines with text additions
            #to counter:
            num_create_adds += pr.additions
            #Add number of lines with text deletions
            #to counter:
            num_create_dels += pr.deletions
            #Check if PR additions greater than max:
            if pr.additions > max_created_pr_adds:
                max_created_pr_adds = pr.additions
                max_created_pr_num = pr.number
            #End if
        #End if

        #check if PR was created by the user,
        #or if no reviews exist for PR, and
        #if so then move on to the next PR:
        if created_pr or (not pr.get_reviews()):
            continue
        #end if

        #check if specified user was a reviewer,
        #and the "review" was not just a comment:
        for review in pr.get_reviews():
            if (review.user.login == username) and \
                (review.state != "COMMENTED" ):
                #Check that review occured during or
                #after provided date:
                submit_date = review.submitted_at.astimezone(denver_time)
                if (submit_date.year > start_year) or \
                (submit_date.year == start_year and \
                submit_date.month >= start_month):
                    #Add one to PR review counter:
                    num_reviewed_prs += 1
                    #Add number of lines with text additions
                    #to counter:
                    num_additions += pr.additions
                    #Add number of lines with text deletions
                    #to counter:
                    num_deletions += pr.deletions
                    #Check if PR additions greater than max:
                    if pr.additions > max_pr_additions:
                        max_pr_additions = pr.additions
                        max_pr_num = pr.number
                    #End if

                else:
                    #Pull requests are now past the cutoff date,
                    #so end the review and PR loops here:
                    stop_loop = True
                    break
                #end if
            #end if
        #end for
    #end for (Pull requests)

    #Notify user that PR loop has finished:
    print(f"...Finished {repo_args[0]}/{repo_args[1]} PR loop.")

    #Close Github connection:
    ghub.close()

    #Print out results:
    print("\n")
    print("-----------------")
    print("PR creation stats")
    print("-----------------")
    print("\n")
    print(f"Total number of PRs opened = {num_created_prs:,}")
    print("\n")
    print(f"Total number of lines with text added = {num_create_adds:,}")
    print("\n")
    print(f"Total number of lines with text removed = {num_create_dels:,}")
    print("\n")
    print(f"Maximum number of additions for single opened PR = {max_created_pr_adds:,}")
    print(f"Maximum additions PR number = {max_created_pr_num:,}")
    print("\n")
    print("-----------------")
    print("PR review stats")
    print("-----------------")
    print("\n")
    print(f"Total number of PRs reviewed = {num_reviewed_prs:,}")
    print("\n")
    print(f"Total number of lines with text added = {num_additions:,}")
    print("\n")
    print(f"Total number of lines with text removed = {num_deletions:,}")
    print("\n")
    print(f"Maximum number of additions for single PR = {max_pr_additions:,}")
    print(f"Maximum additions PR number = {max_pr_num:,}")

###############################################################################
if __name__ == "__main__":
    main_script()
