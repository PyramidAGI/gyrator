import random
import nltk

# Ensure the word list is downloaded
#nltk.download('words')

# Get English words
english_words = set(w.lower() for w in nltk.corpus.words.words())

# Generate 10 random words
random_words = random.sample(list(english_words), 10)

print(random_words)