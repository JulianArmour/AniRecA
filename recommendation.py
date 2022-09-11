import requests
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


def fetch_user_completed_list_recs(username):
    response = requests.post(
        GRAPHQL_URI, json={"query": COMPLETED_ANIME_RECS_QUERY, "variables": {"username": username}}
    )
    return response.json()


def aggregate_recommendations(completed_anime_recs, rec_type, min_user_score):
    entries = completed_anime_recs['data']['MediaListCollection']['lists'][0]['entries']
    my_watched_anime = [(entry['media']['id'], entry['media']['title']['romaji']) for entry in entries]
    my_watched_anime_keys = set(id for (id, _) in my_watched_anime)
    rec_vals = defaultdict(float)

    for entry in entries:
        score = entry["score"]
        entry_weight = score / 100
        if score < min_user_score:
            continue
        for rec in entry['media']['recommendations']['edges']:
            media = rec['node']['mediaRecommendation']
            rating = rec['node']['rating']
            if media is None:
                continue
            if media['id'] not in my_watched_anime_keys:
                if rec_type == "recommendations_by_mode":
                    rec_vals[media['title']['romaji']] += 1
                elif rec_type == "recommendations_by_weighted_mode":
                    rec_vals[media['title']['romaji']] += entry_weight
                else:
                    rec_vals[media['title']['romaji']] += entry_weight * rating

    recommendations = [(name, int(vals)) for name, vals in rec_vals.items()] 
    recommendations.sort(key=lambda recommendation: recommendation[1], reverse=True)
    return recommendations


def recommendations(username, rec_type="", min_user_score=0):
    list_data = fetch_user_completed_list_recs(username)
    recommendations = aggregate_recommendations(list_data, rec_type, min_user_score)
    for name, val in recommendations:
        print(f"{val}\t{name}", sep="\t")


def main():
    recommendations("SimpleCore")


if __name__ == "__main__":
    main()
