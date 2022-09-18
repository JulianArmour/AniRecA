import requests
import argparse
from collections import defaultdict


GRAPHQL_URI = "https://graphql.anilist.co"

COMPLETED_ANIME_RECS_QUERY = """
query CompletedRecs($username: String) {
  MediaListCollection(userName:$username, type:ANIME, status:COMPLETED, sort:SCORE_DESC) {
    lists {
      entries {
        score(format: POINT_100)
        media {
          id
          title {
            english
            romaji
          }
          recommendations(sort:RATING_DESC, page:0, perPage:10) {
            edges {
              node {
                rating
                mediaRecommendation {
                  id
                  title{
                    english
                    romaji
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

DROPPED_ANIME_QUERY = """
query DroppedAnime($username: String) {
  MediaListCollection(userName:$username, type:ANIME, status:DROPPED) {
    lists {
      entries {
        media {
          id
        }
      }
    }
  }
}
"""


def fetch_user_completed_list_recs(username):
    response = requests.post(
        GRAPHQL_URI,
        json={"query": COMPLETED_ANIME_RECS_QUERY, "variables": {"username": username}},
    )
    return response.json()


def fetch_user_dropped_list(username):
    response = requests.post(
        GRAPHQL_URI,
        json={"query": DROPPED_ANIME_QUERY, "variables": {"username": username}},
    )
    return response.json()


def aggregate_recommendations(
    completed_anime_recs, metric_type, min_user_score, exclude_ids=None
):
    entries = completed_anime_recs["data"]["MediaListCollection"]["lists"][0]["entries"]
    my_watched_anime = [
        (entry["media"]["id"], entry["media"]["title"]["romaji"]) for entry in entries
    ]
    # we dont' want to recommend anime a user has already seen
    my_watched_anime_keys = set(id for (id, _) in my_watched_anime)
    if exclude_ids:
        my_watched_anime_keys |= set(exclude_ids)
    rec_vals = defaultdict(float)

    for entry in entries:
        score = entry["score"]
        entry_weight = score / 100
        if score < min_user_score:
            continue
        for rec in entry["media"]["recommendations"]["edges"]:
            media = rec["node"]["mediaRecommendation"]
            rating = rec["node"]["rating"]
            if media is None:
                continue
            if media["id"] not in my_watched_anime_keys:
                if metric_type == "mode":
                    rec_vals[media["title"]["romaji"]] += 1
                elif metric_type == "weighted_mode":
                    rec_vals[media["title"]["romaji"]] += entry_weight
                else:
                    rec_vals[media["title"]["romaji"]] += entry_weight * rating

    recommendations = [(name, int(vals)) for name, vals in rec_vals.items()]
    recommendations.sort(key=lambda recommendation: recommendation[1], reverse=True)
    return recommendations


def recommendations(username, metric_type="", min_user_score=0):
    list_data = fetch_user_completed_list_recs(username)
    dropped_anime_data = fetch_user_dropped_list(username)
    dropped_anmime_ids = [
        entry["media"]["id"]
        for entry in dropped_anime_data["data"]["MediaListCollection"]["lists"][0][
            "entries"
        ]
    ]
    recommendations = aggregate_recommendations(
        list_data, metric_type, min_user_score, exclude_ids=dropped_anmime_ids
    )
    for name, val in recommendations:
        print(f"{val}\t{name}", sep="\t")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u",
        "--username",
        required=True,
        help="Username for which to aggregate recommendations",
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=["mode", "weighted_mode", "weighted_ratings"],
        default="weighted_ratings",
        help="Type of metric used to rank recommendations (default: %(default)s)."
        " mode - the frequency a recommendations appears."
        " weighted_mode - same as mode, but recommendations weight more for anime the user has scored higher."
        " weighted_ratings - same as weighted_mode, but the ratings associated with the recommendation are used"
        " instead of frequency."
        " Generally, weighted_ratings results in the best recommendations.",
    )
    parser.add_argument(
        "-m",
        "--min-score",
        type=int,
        choices=range(0, 11),
        default=0,
        help="Only aggregate recommendations for anime the user scored at least as high as this number.",
    )
    args = parser.parse_args()
    recommendations(args.username, metric_type=args.type, min_user_score=args.min_score)


if __name__ == "__main__":
    main()
