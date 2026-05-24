import random
#Alfarouq Ibrahim Task 1 Hangman game
words = ["gogo gaga" , "oh mamamia" , "omg its abdalbaset hamoda" , "Team shoky" , "lotfy" , "jafa" , "Alsharqia Vibes"]
target_word = random.choice(words)

guesses_left = 6
guessed_letters = []

print("Welcome to Hangman game!")

while guesses_left > 0:

    display_word = ""
    for letter in target_word:
        if letter == " ":
            display_word += " "
        elif letter in guessed_letters:
            display_word += letter + " "
        else:
            display_word += "_ "

    print("\n The word: " + display_word)
    print("You have " + str(guesses_left) + " guesses left.")

    if "_" not in display_word:
        print("You win!")
        break

    guess = input("Enter your guess: ").lower()

    if len(guess) != 1 or not guess.isalpha():
        print("Please enter a valid letter.")
        continue

    if guess in guessed_letters:
        print ("You already guessed this letter.")
        continue

    guessed_letters.append(guess)

    if guess not in target_word:
        guesses_left -= 1
        print("You have " + str(guesses_left) + " guesses left.")
    else :
        print ("You guessed this letter.")

    if guesses_left == 0:
        print("You lose! The word was " + target_word)

