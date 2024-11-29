import tweepy
import pandas as pd
import time
import sys

def load_client(bearer_token):
    """
    Initialisation du client Tweepy qui communique avec l'API de X avec son Bearer token.
    
    Args:
        bearer_token (str): Le token Bearer pour accéder à l'API Twitter.
    
    Retourne:
        tweepy.Client: Client Tweepy initialisé.
    """
    try:
        client = tweepy.Client(bearer_token)
        return client
    except Exception as e:
        print(f"Erreur lors de l'initialisation du client Tweepy : {e}")
        raise

def fetch_tweets(client, keyword, max_results=10):
    """
    Recherche des tweets récents en fonction d'un mot-clé.

    Args:
        client (tweepy.Client): Client Tweepy.
        keyword (str): Mot-clé pour la recherche.
        max_results (int): Nombre maximum de tweets à récupérer (par défaut/minimun 10).
    
    Retourne:
        dict: Données des tweets, utilisateurs et lieux.
    """
    tweet_fields = [
        "id", "text", "created_at", "attachments", "author_id", "in_reply_to_user_id",
        "lang", "possibly_sensitive", "context_annotations", "public_metrics", "referenced_tweets"
    ]
    user_fields = [
        "id", "name", "username", "description", "location", "public_metrics", "verified"
    ]
    place_fields = ["id", "full_name", "country"]

    try:
        response = client.search_recent_tweets(
            query=f"{keyword} lang:en", # On peut cibler un type de langue précis).
            max_results=max_results,
            tweet_fields=tweet_fields,
            user_fields=user_fields,
            place_fields=place_fields,
            expansions=["author_id", "geo.place_id"]
        )
        return {
            "tweets": response.data,
            "users": response.includes.get("users", []),
            "places": response.includes.get("places", [])
        }
    except tweepy.errors.TooManyRequests as e:
        reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + 60))
        wait_time = max(0, reset_time - int(time.time()))
        print(f"Limite de requêtes atteinte. Réessayez après {wait_time} secondes. Fin du programme.")
        sys.exit(0)  # Quitte le programme proprement avec un code de sortie 0.
    except Exception as e:
        print(f"Erreur lors de la récupération des tweets : {e}")
        return {"tweets": [], "users": [], "places": []}

def process_tweets(data):
    """
    Traite les données des tweets et les organise dans un DataFrame.

    Args:
        data (dict): Données des tweets, utilisateurs et lieux.

    Retourne:
        pd.DataFrame: DataFrame contenant les informations traitées.
    """
    try:
        tweets = data["tweets"]
        users_data = {user["id"]: user for user in data["users"]}
        places_data = {place["id"]: place for place in data["places"]}

        tweets_data = []
        for tweet in tweets:
            # Ajoute les informations du tweets.
            tweet_info = {
                "tweet_id": tweet.id,
                "text": tweet.text,
                "created_at": tweet.created_at,
                "author_id": tweet.author_id,
                "lang": tweet.lang,
                "possibly_sensitive": tweet.possibly_sensitive,
                "retweets": tweet.public_metrics["retweet_count"],
                "replies": tweet.public_metrics["reply_count"],
                "likes": tweet.public_metrics["like_count"],
                "quotes": tweet.public_metrics["quote_count"],
            }

            # Ajoute les informations sur l'auteur.
            if tweet.author_id in users_data:
                user = users_data[tweet.author_id]
                tweet_info.update({
                    "user_name": user.name,
                    "username": user.username,
                    "user_description": user.description,
                    "user_location": user.location,
                    "followers_count": user.public_metrics["followers_count"],
                    "following_count": user.public_metrics["following_count"],
                    "tweet_count": user.public_metrics["tweet_count"],
                    "verified": user.verified,
                })

            # Ajoute les informations sur le lieu.
            if tweet.geo and tweet.geo.get("place_id") in places_data:
                place = places_data[tweet.geo["place_id"]]
                tweet_info.update({
                    "place_name": place.full_name,
                    "place_country": place.country,
                })

            tweets_data.append(tweet_info)

        return pd.DataFrame(tweets_data)
    except Exception as e:
        print(f"Erreur lors du traitement des tweets : {e}")
        return pd.DataFrame()

def save_to_csv(df, output_file):
    """
    Sauvegarde un DataFrame dans un fichier CSV.

    Args:
        df (pd.DataFrame): DataFrame à sauvegarder.
        output_file (str): Chemin du fichier CSV.
    """
    try:
        df.to_csv(output_file, index=False, encoding="utf-8")
        print(f"Les données des tweets ont été enregistrées dans : {output_file}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier CSV : {e}")

def main(keyword, output_file, bearer_token):
    """
    Fonction principale pour récupérer et sauvegarder des tweets.

    Args:
        keyword (str): Mot-clé pour la recherche.
        output_file (str): Chemin du fichier CSV en sortie.
        bearer_token (str): Token Bearer pour l'API de X.
    """
    try:
        print("Initialisation du client Tweepy...")
        client = load_client(bearer_token)

        print("Recherche des tweets...")
        data = fetch_tweets(client, keyword)

        print("Traitement des tweets...")
        if data["tweets"]:
            df = process_tweets(data)
            save_to_csv(df, output_file)
        else:
            print("Aucun tweet trouvé.")
    except Exception as e:
        print(f"Erreur dans la fonction principale : {e}")

if __name__ == "__main__":
    import argparse

    # Configuration des arguments de la ligne de commande.
    parser = argparse.ArgumentParser(description="Recherche et sauvegarde des tweets dans un fichier CSV.")
    parser.add_argument("keyword", type=str, help="Mot-clé pour la recherche de tweets.")
    parser.add_argument("output_file", type=str, help="Chemin du fichier CSV en sortie.")
    parser.add_argument("bearer_token", type=str, help="Token Bearer pour accéder à l'API de X.")
    
    args = parser.parse_args()

    # Exécution de la fonction principale
    main(args.keyword, args.output_file, args.bearer_token)
