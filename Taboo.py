import os
import sqlite3
import random
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackQueryHandler
)

# Logging Setup For Tracking
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Global State Management
Lobby_Data = {
    "Is_Open": False,
    "Creator_Id": None,
    "Players": [],
    "Player_Names": {}
}

Game_State = {
    "Is_Running": False,
    "Team_A": [],
    "Team_B": [],
    "Scores": {"A": 0, "B": 0},
    "Current_Turn_Team": "A",
    "Current_Word": None,
    "Taboo_Words": [],
    "Clue_Giver": None,
    "Category": "General",
    "Round_Active": False
}

# Database Core Functions
Conn = sqlite3.connect('Taboo_Master.db', check_same_thread=False)
Cursor = Conn.cursor()

def Initialize_System():
    Cursor.execute('''Create Table If Not Exists Players 
                    (User_Id Integer Primary Key, Name Text, Points Integer Default 0, Wins Integer Default 0, Games_Played Integer Default 0)''')
    Conn.commit()

Initialize_System()

def Update_Stats(user_id, name, pts=0, win=0):
    Cursor.execute("Select User_Id From Players Where User_Id = ?", (user_id,))
    if not Cursor.fetchone():
        Cursor.execute("Insert Into Players (User_Id, Name, Points, Wins, Games_Played) Values (?, ?, ?, ?, 1)", (user_id, name, pts, win))
    else:
        Cursor.execute("Update Players Set Points = Points + ?, Wins = Wins + ?, Games_Played = Games_Played + 1 Where User_Id = ?", (pts, win, user_id))
    Conn.commit()

# Massive Word Database
Word_Library = [
    {"Word": "Samosa", "Taboo": ["Aloo", "Chutney", "Snack", "Fried", "Tea"]},
    {"Word": "Cricket", "Taboo": ["Bat", "Ball", "Dhoni", "Kohli", "Wicket"]},
    {"Word": "Mobile", "Taboo": ["Phone", "Call", "Screen", "App", "Battery"]},
    {"Word": "Salman", "Taboo": ["Bhai", "Tiger", "Actor", "Bollywood", "Six-Pack"]},
    {"Word": "Internet", "Taboo": ["Wifi", "Google", "Data", "Online", "Website"]},
    {"Word": "Biryani", "Taboo": ["Rice", "Chicken", "Food", "Dinner", "Spicy"]},
    {"Word": "YouTube", "Taboo": ["Video", "Channel", "Subscribe", "Google", "Vlog"]},
    {"Word": "Helmet", "Taboo": ["Bike", "Head", "Safety", "Police", "Ride"]},
    {"Word": "Laptop", "Taboo": ["Computer", "Keyboard", "Work", "Dell", "Screen"]},
    {"Word": "Cinema", "Taboo": ["Movie", "Theater", "Popcorn", "Ticket", "Screen"]},
    {"Word": "Metro", "Taboo": ["Train", "Token", "Delhi", "Card", "Travel"]},
    {"Word": "Maggi", "Taboo": ["Noodles", "2 Minutes", "Masala", "Snack", "Hungry"]},
    {"Word": "Taj Mahal", "Taboo": ["Agra", "Love", "Shah Jahan", "Marble", "White"]},
    {"Word": "Instagram", "Taboo": ["Reels", "Post", "Story", "Like", "Follow"]},
    {"Word": "Chai", "Taboo": ["Tea", "Milk", "Sugar", "Cup", "Morning"]},
    {"Word": "Train", "Taboo": ["Station", "Track", "Journey", "Ticket", "Berth"]},
    {"Word": "Modi", "Taboo": ["PM", "India", "Leader", "BJP", "Gujarat"]},
    {"Word": "Pizza", "Taboo": ["Cheese", "Dominos", "Italian", "Food", "Slice"]},
    {"Word": "Joker", "Taboo": ["Cards", "Movie", "Batman", "Funny", "Circus"]},
    {"Word": "Doctor", "Taboo": ["Hospital", "Medicine", "Patient", "Nurse", "Clinic"]},
    {"Word": "WhatsApp", "Taboo": ["Chat", "Status", "Message", "Group", "Call"]},
    {"Word": "Pubg", "Taboo": ["Game", "Mobile", "Winner", "Chicken Dinner", "Gun"]},
    {"Word": "Ice Cream", "Taboo": ["Cold", "Cone", "Chocolate", "Sweet", "Milk"]},
    {"Word": "Zomato", "Taboo": ["Food", "Delivery", "App", "Order", "Restaurant"]},
    {"Word": "Netflix", "Taboo": ["Series", "Movies", "Watch", "Subscription", "Online"]},
    {"Word": "Amazon", "Taboo": ["Delivery", "Shopping", "Jeff Bezos", "Prime", "Package"]},
    {"Word": "Apple", "Taboo": ["iPhone", "Fruit", "Steve Jobs", "MacBook", "Red"]},
    {"Word": "Google", "Taboo": ["Search", "Internet", "Browser", "Alphabet", "Answer"]},
    {"Word": "Facebook", "Taboo": ["Mark Zuckerberg", "Meta", "Social Media", "Friends", "Blue"]},
    {"Word": "Tesla", "Taboo": ["Elon Musk", "Electric", "Car", "Battery", "SpaceX"]},
    {"Word": "Microsoft", "Taboo": ["Bill Gates", "Windows", "Office", "Computer", "Software"]},
    {"Word": "Disney", "Taboo": ["Mickey Mouse", "Cartoons", "Movies", "World", "Land"]},
    {"Word": "Nike", "Taboo": ["Shoes", "Just Do It", "Sports", "Brand", "Swoosh"]},
    {"Word": "Adidas", "Taboo": ["Shoes", "Sports", "Three Stripes", "Brand", "German"]},
    {"Word": "Starbucks", "Taboo": ["Coffee", "Cafe", "Green", "Drink", "Brew"]},
    {"Word": "McDonalds", "Taboo": ["Burger", "Fries", "Fast Food", "Clown", "Golden Arches"]},
    {"Word": "Coca Cola", "Taboo": ["Drink", "Soda", "Red", "Bottle", "Beverage"]},
    {"Word": "Pepsi", "Taboo": ["Drink", "Soda", "Blue", "Bottle", "Beverage"]},
    {"Word": "Toyota", "Taboo": ["Car", "Japan", "Vehicle", "Engine", "Drive"]},
    {"Word": "Honda", "Taboo": ["Car", "Bike", "Japan", "Engine", "Drive"]},
    {"Word": "Samsung", "Taboo": ["Mobile", "TV", "Korea", "Electronics", "Galaxy"]},
    {"Word": "Sony", "Taboo": ["PlayStation", "TV", "Electronics", "Japan", "Camera"]},
    {"Word": "Marvel", "Taboo": ["Avengers", "Comics", "Iron Man", "Superhero", "Movies"]},
    {"Word": "Harry Potter", "Taboo": ["Magic", "Wizard", "Hogwarts", "Wand", "JK Rowling"]},
    {"Word": "Star Wars", "Taboo": ["Jedi", "Space", "Luke Skywalker", "Darth Vader", "Force"]},
    {"Word": "Batman", "Taboo": ["Joker", "Gotham", "Dark Knight", "DC", "Bruce Wayne"]},
    {"Word": "Superman", "Taboo": ["Clark Kent", "Kryptonite", "DC", "Cape", "Fly"]},
    {"Word": "Spider-Man", "Taboo": ["Peter Parker", "Marvel", "Web", "Spider", "Red"]},
    {"Word": "Inception", "Taboo": ["Dream", "Christopher Nolan", "Leonardo DiCaprio", "Spinning Top", "Movie"]},
    {"Word": "Titanic", "Taboo": ["Ship", "Iceberg", "Jack", "Rose", "Movie"]},
    {"Word": "Jurassic Park", "Taboo": ["Dinosaur", "Steven Spielberg", "T-Rex", "Island", "Movie"]},
    {"Word": "The Lion King", "Taboo": ["Simba", "Disney", "Hakuna Matata", "Mufasa", "Movie"]},
    {"Word": "Toy Story", "Taboo": ["Woody", "Buzz Lightyear", "Disney", "Toys", "Movie"]},
    {"Word": "Frozen", "Taboo": ["Elsa", "Anna", "Disney", "Olaf", "Snow"]},
    {"Word": "The Avengers", "Taboo": ["Iron Man", "Captain America", "Thor", "Hulk", "Marvel"]},
    {"Word": "Black Panther", "Taboo": ["Wakanda", "Marvel", "Chadwick Boseman", "Superhero", "Movie"]},
    {"Word": "Wonder Woman", "Taboo": ["Gal Gadot", "DC", "Amazon", "Superhero", "Movie"]},
    {"Word": "Shrek", "Taboo": ["Ogre", "Donkey", "Fiona", "Green", "Movie"]},
    {"Word": "Minions", "Taboo": ["Yellow", "Despicable Me", "Gru", "Banana", "Movie"]},
    {"Word": "Game of Thrones", "Taboo": ["Dragons", "Jon Snow", "Winter", "Throne", "Series"]},
    {"Word": "Friends", "Taboo": ["Joey", "Rachel", "Chandler", "Coffee Shop", "Series"]},
    {"Word": "Breaking Bad", "Taboo": ["Walter White", "Jesse Pinkman", "Chemistry", "Blue", "Series"]},
    {"Word": "Stranger Things", "Taboo": ["Eleven", "Upside Down", "Demogorgon", "Netflix", "Series"]},
    {"Word": "The Simpsons", "Taboo": ["Homer", "Bart", "Yellow", "Cartoon", "Series"]},
    {"Word": "The Big Bang Theory", "Taboo": ["Sheldon", "Leonard", "Penny", "Science", "Series"]},
    {"Word": "The Office", "Taboo": ["Michael Scott", "Dwight", "Jim", "Pam", "Series"]},
    {"Word": "Sherlock", "Taboo": ["Benedict Cumberbatch", "Watson", "Detective", "London", "Series"]},
    {"Word": "Doctor Who", "Taboo": ["TARDIS", "Time Travel", "The Doctor", "Daleks", "Series"]},
    {"Word": "Pokemon", "Taboo": ["Pikachu", "Ash Ketchum", "Catch", "Nintendo", "Cards"]},
    {"Word": "Super Mario", "Taboo": ["Nintendo", "Luigi", "Peach", "Bowser", "Video Game"]},
    {"Word": "Legend of Zelda", "Taboo": ["Link", "Zelda", "Nintendo", "Master Sword", "Video Game"]},
    {"Word": "Minecraft", "Taboo": ["Blocks", "Building", "Creeper", "Steve", "Video Game"]},
    {"Word": "Fortnite", "Taboo": ["Battle Royale", "Building", "Emotes", "Epic Games", "Video Game"]},
    {"Word": "Call of Duty", "Taboo": ["Shooting", "War", "Multiplayer", "Activision", "Video Game"]},
    {"Word": "Grand Theft Auto", "Taboo": ["GTA", "Rockstar Games", "Car", "Crime", "Video Game"]},
    {"Word": "FIFA", "Taboo": ["Football", "Video Game", "EA Sports", "Soccer", "Cards"]},
    {"Word": "The Witcher", "Taboo": ["Geralt", "Monsters", "Magic", "Netflix", "Video Game"]},
    {"Word": "Assassin's Creed", "Taboo": ["History", "Assassin", "Ubisoft", "Stealth", "Video Game"]},
    {"Word": "Skyrim", "Taboo": ["Dragons", "Open World", "RPG", "Bethesda", "Video Game"]},
    {"Word": "Final Fantasy", "Taboo": ["RPG", "Cloud Strife", "Square Enix", "Magic", "Video Game"]},
    {"Word": "World of Warcraft", "Taboo": ["MMORPG", "Blizzard", "Horde", "Alliance", "Video Game"]},
    {"Word": "Overwatch", "Taboo": ["Heroes", "Shooting", "Blizzard", "Multiplayer", "Video Game"]},
    {"Word": "League of Legends", "Taboo": ["MOBA", "Riot Games", "Heroes", "Strategy", "Video Game"]},
    {"Word": "Dota 2", "Taboo": ["MOBA", "Valve", "Heroes", "Strategy", "Video Game"]},
    {"Word": "Counter-Strike", "Taboo": ["Shooting", "Valve", "Multiplayer", "War", "Video Game"]},
    {"Word": "Pac-Man", "Taboo": ["Arcade", "Ghosts", "Eating", "Yellow", "Video Game"]},
    {"Word": "Tetris", "Taboo": ["Blocks", "Puzzle", "Lines", "Russia", "Video Game"]},
    {"Word": "Chess", "Taboo": ["Board Game", "King", "Queen", "Checkmate", "Strategy"]},
    {"Word": "Monopoly", "Taboo": ["Board Game", "Money", "Property", "Hotel", "Dice"]},
    {"Word": "Scrabble", "Taboo": ["Board Game", "Words", "Letters", "Points", "Tiles"]},
    {"Word": "Catan", "Taboo": ["Board Game", "Resources", "Building", "Settlers", "Strategy"]},
    {"Word": "Ticket to Ride", "Taboo": ["Board Game", "Trains", "Routes", "Travel", "Strategy"]},
    {"Word": "Pandemic", "Taboo": ["Board Game", "Disease", "Cooperative", "Strategy", "Virus"]},
    {"Word": "Risk", "Taboo": ["Board Game", "War", "Strategy", "World Domination", "Dice"]},
    {"Word": "Clue", "Taboo": ["Board Game", "Murder", "Mystery", "Detective", "Mansion"]},
    {"Word": "Uno", "Taboo": ["Card Game", "Numbers", "Colors", "Reverse", "Wild Card"]},
    {"Word": "Poker", "Taboo": ["Card Game", "Gambling", "Chips", "Bluffing", "Strategy"]},
    {"Word": "Bridge", "Taboo": ["Card Game", "Strategy", "Partnership", "Bidding", "Trick-taking"]},
    {"Word": "Solitaire", "Taboo": ["Card Game", "Single Player", "Cards", "Patience", "Computer"]},
    {"Word": "Rummy", "Taboo": ["Card Game", "Sets", "Runs", "Strategy", "Cards"]},
    {"Word": "Blackjack", "Taboo": ["Card Game", "21", "Casino", "Gambling", "Strategy"]},
    {"Word": "Baccarat", "Taboo": ["Card Game", "Casino", "Gambling", "Strategy", "James Bond"]},
    {"Word": "Sudoku", "Taboo": ["Puzzle", "Numbers", "Grid", "Logic", "Math"]},
    {"Word": "Crossword", "Taboo": ["Puzzle", "Words", "Clues", "Newspaper", "Letters"]},
    {"Word": "Rubik's Cube", "Taboo": ["Puzzle", "Colors", "Cube", "Logic", "Twist"]},
    {"Word": "Football", "Taboo": ["Soccer", "Ball", "Goal", "Pitch", "Sport"]},
    {"Word": "Basketball", "Taboo": ["Hoop", "Ball", "Court", "Dunk", "Sport"]},
    {"Word": "Tennis", "Taboo": ["Racket", "Ball", "Court", "Net", "Sport"]},
    {"Word": "Golf", "Taboo": ["Club", "Ball", "Course", "Hole", "Sport"]},
    {"Word": "Baseball", "Taboo": ["Bat", "Ball", "Field", "Home Run", "Sport"]},
    {"Word": "Rugby", "Taboo": ["Ball", "Pitch", "Scrum", "Tackle", "Sport"]},
    {"Word": "American Football", "Taboo": ["Ball", "Field", "Touchdown", "NFL", "Sport"]},
    {"Word": "Hockey", "Taboo": ["Stick", "Puck", "Ice", "Goal", "Sport"]},
    {"Word": "Volleyball", "Taboo": ["Ball", "Net", "Court", "Spike", "Sport"]},
    {"Word": "Swimming", "Taboo": ["Water", "Pool", "Laps", "Race", "Sport"]},
    {"Word": "Athletics", "Taboo": ["Running", "Track", "Field", "Race", "Sport"]},
    {"Word": "Cycling", "Taboo": ["Bicycle", "Race", "Road", "Helmet", "Sport"]},
    {"Word": "Boxing", "Taboo": ["Gloves", "Ring", "Punch", "Fight", "Sport"]},
    {"Word": "Martial Arts", "Taboo": ["Karate", "Judo", "Fight", "Belt", "Sport"]},
    {"Word": "Yoga", "Taboo": ["Stretching", "Meditation", "Exercise", "Mat", "Sport"]},
    {"Word": "Gymnastics", "Taboo": ["Flip", "Floor", "Beam", "Vault", "Sport"]},
    {"Word": "Skiing", "Taboo": ["Snow", "Mountain", "Skis", "Winter", "Sport"]},
    {"Word": "Snowboarding", "Taboo": ["Snow", "Mountain", "Board", "Winter", "Sport"]},
    {"Word": "Surfing", "Taboo": ["Water", "Ocean", "Waves", "Board", "Sport"]},
    {"Word": "Sailing", "Taboo": ["Water", "Boat", "Wind", "Ocean", "Sport"]},
    {"Word": "Mountain Climbing", "Taboo": ["Mountain", "Climbing", "Rope", "Peak", "Sport"]},
    {"Word": "Hiking", "Taboo": ["Walking", "Mountain", "Trail", "Nature", "Sport"]},
    {"Word": "Camping", "Taboo": ["Tent", "Nature", "Outdoors", "Fire", "Sleep"]},
    {"Word": "Fishing", "Taboo": ["Water", "Fish", "Rod", "Hook", "Sport"]},
    {"Word": "Hunting", "Taboo": ["Animals", "Gun", "Bow", "Wild", "Sport"]},
    {"Word": "Gardening", "Taboo": ["Plants", "Flowers", "Yard", "Soil", "Growing"]},
    {"Word": "Cooking", "Taboo": ["Food", "Kitchen", "Recipe", "Eating", "Chef"]},
    {"Word": "Baking", "Taboo": ["Food", "Oven", "Recipe", "Cake", "Bread"]},
    {"Word": "Painting", "Taboo": ["Art", "Artist", "Brush", "Canvas", "Color"]},
    {"Word": "Drawing", "Taboo": ["Art", "Artist", "Pencil", "Paper", "Sketch"]},
    {"Word": "Photography", "Taboo": ["Camera", "Photos", "Pictures", "Image", "Lens"]},
    {"Word": "Music", "Taboo": ["Sound", "Song", "Instrument", "Listen", "Artist"]},
    {"Word": "Singing", "Taboo": ["Voice", "Music", "Song", "Artist", "Mouth"]},
    {"Word": "Dancing", "Taboo": ["Movement", "Music", "Rhythm", "Party", "Body"]},
    {"Word": "Writing", "Taboo": ["Words", "Paper", "Pen", "Book", "Story"]},
    {"Word": "Reading", "Taboo": ["Book", "Words", "Eyes", "Story", "Library"]},
    {"Word": "Traveling", "Taboo": ["Trip", "Journey", "Vacation", "Airplane", "World"]},
    {"Word": "Shopping", "Taboo": ["Store", "Buy", "Money", "Package", "Mall"]},
    {"Word": "Movies", "Taboo": ["Cinema", "Film", "Watch", "Theater", "Popcorn"]},
    {"Word": "Television", "Taboo": ["TV", "Watch", "Screen", "Series", "Shows"]},
    {"Word": "Radio", "Taboo": ["Sound", "Music", "Listen", "Station", "Broadcasting"]},
    {"Word": "Podcasts", "Taboo": ["Listen", "Sound", "Series", "Internet", "Talking"]},
    {"Word": "Social Media", "Taboo": ["Internet", "Friends", "Post", "Like", "Follow"]},
    {"Word": "Video Games", "Taboo": ["Play", "Screen", "Console", "Controller", "Fun"]},
    {"Word": "Internet Browsing", "Taboo": ["Search", "Website", "Internet", "Browser", "Online"]},
    {"Word": "Coding", "Taboo": ["Computer", "Programming", "Software", "Code", "Developer"]}
]

# Timer Logic Function
async def Manage_Round_Timer(chat_id, context, round_word):
    await asyncio.sleep(30)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        await context.bot.send_message(chat_id=chat_id, text="Time Alert Only Ninety Seconds Remaining\nHurry Up And Provide Better Clues To Your Team")

    await asyncio.sleep(30)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        await context.bot.send_message(chat_id=chat_id, text="Time Alert Only Sixty Seconds Remaining\nThe Clock Is Ticking Fast Make Your Guess Quickly")

    await asyncio.sleep(30)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        await context.bot.send_message(chat_id=chat_id, text="Time Alert Final Thirty Seconds Remaining\nThis Is Your Last Chance To Score Points In This Round")

    await asyncio.sleep(30)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Game_State["Round_Active"] = False
        Game_State["Current_Word"] = None
        current = Game_State["Current_Turn_Team"]
        Game_State["Current_Turn_Team"] = "B" if current == "A" else "A"
        
        Final_Msg = "Round Over The Time Has Fully Expired\n\n"
        Final_Msg += "The Correct Word Was " + round_word + "\n"
        Final_Msg += "No Points Were Awarded To Any Team This Time\n\n"
        Final_Msg += "The Turn Has Now Shifted To The Other Team\n"
        Final_Msg += "Please Type /Next To Begin The Following Round"
        await context.bot.send_message(chat_id=chat_id, text=Final_Msg)

# Command Handlers
async def Help_Handler(update: Update, context):
    Guide = "Welcome To The Professional Taboo Gaming Bot Help Menu\n\n"
    Guide += "Available Commands For Managing Your Session\n"
    Guide += "1. /Lobby Create A New Gaming Room For Your Friends\n"
    Guide += "2. /Join Enter An Already Created Active Lobby\n"
    Guide += "3. /Start Begin The Game Match Once Teams Are Ready\n"
    Guide += "4. /Next Fetch The New Secret Word In Your Private Chat\n"
    Guide += "5. /Status View The Current Scoreboard And Match Info\n"
    Guide += "6. /Profile View Your Personal Statistics And Career Points\n"
    Guide += "7. /Leaderboard See The Global Ranking Of Top Players\n"
    Guide += "8. /Reset Terminate The Current Session And Start Fresh\n\n"
    Guide += "Enjoy Your Game And Play Fair To Climb The Ranks"
    await update.message.reply_text(Guide)

async def Lobby_Handler(update: Update, context):
    if Lobby_Data["Is_Open"]: 
        return await update.message.reply_text("Warning An Active Lobby Is Already In Operation")
    user = update.message.from_user
    Lobby_Data.update({"Is_Open": True, "Creator_Id": user.id, "Players": [user.id], "Player_Names": {user.id: user.first_name}})
    
    Invite = "A New Taboo Gaming Lobby Has Been Successfully Created\n\n"
    Invite += "Host Name " + user.first_name + "\n"
    Invite += "Status Waiting For Players To Join The Session\n\n"
    Invite += "Instructions For Joining Participants\n"
    Invite += "Type /Join To Enter This Room Right Now\n"
    Invite += "Type /Start Once All Participants Are Present\n"
    Invite += "Minimum Of Two Players Required For Match Activation"
    await update.message.reply_text(Invite)

async def Join_Handler(update: Update, context):
    user = update.message.from_user
    if not Lobby_Data["Is_Open"]: 
        return await update.message.reply_text("Error No Active Lobby Found To Join At This Moment")
    if user.id in Lobby_Data["Players"]: 
        return await update.message.reply_text("Information You Are Already A Member Of This Lobby")
    
    Lobby_Data["Players"].append(user.id)
    Lobby_Data["Player_Names"][user.id] = user.first_name
    
    Update_Msg = user.first_name + " Has Joined The Game Lobby Successfully\n\n"
    Update_Msg += "Current Participant Count " + str(len(Lobby_Data["Players"])) + "\n"
    Update_Msg += "Waiting For More Friends To Join The Fun\n"
    Update_Msg += "Invite Others By Sharing The Group Link Immediately"
    await update.message.reply_text(Update_Msg)

async def Start_Handler(update: Update, context):
    if not Lobby_Data["Is_Open"] or update.message.from_user.id != Lobby_Data["Creator_Id"]:
        return await update.message.reply_text("Permission Denied Only The Creator Can Initialize The Match")
    if len(Lobby_Data["Players"]) < 2:
        return await update.message.reply_text("Insufficient Players Required At Least Two For Start")
    
    random.shuffle(Lobby_Data["Players"])
    mid = len(Lobby_Data["Players"]) // 2
    Game_State.update({
        "Is_Running": True, 
        "Team_A": Lobby_Data["Players"][:mid], 
        "Team_B": Lobby_Data["Players"][mid:], 
        "Scores": {"A": 0, "B": 0}
    })
    Lobby_Data["Is_Open"] = False
    
    Battle_Msg = "The Game Has Commenced And Teams Are Now Locked\n\n"
    Battle_Msg += "Members Of Team A\n"
    for p_id in Game_State["Team_A"]: Battle_Msg += "- " + Lobby_Data["Player_Names"][p_id] + "\n"
    Battle_Msg += "\nMembers Of Team B\n"
    for p_id in Game_State["Team_B"]: Battle_Msg += "- " + Lobby_Data["Player_Names"][p_id] + "\n"
    Battle_Msg += "\nStarting Round With Team A Ready Your Guesses\n"
    Battle_Msg += "Please Type /Next To See Your First Secret Word"
    await update.message.reply_text(Battle_Msg)

async def Next_Round_Handler(update: Update, context):
    if not Game_State["Is_Running"]: 
        return await update.message.reply_text("No Match Is Currently Running At The Moment")
    
    team_key = "Team_" + Game_State["Current_Turn_Team"]
    Game_State["Clue_Giver"] = random.choice(Game_State[team_key])
    word_obj = random.choice(Word_Library)
    
    Game_State.update({
        "Current_Word": word_obj["Word"],
        "Taboo_Words": [w.lower() for w in word_obj["Taboo"]],
        "Round_Active": True
    })

    try:
        Dm_Msg = "Your Secret Taboo Details Are Provided Below\n\n"
        Dm_Msg += "Main Secret Word " + word_obj['Word'] + "\n\n"
        Dm_Msg += "Restricted Taboo Words To Avoid\n"
        for w in word_obj['Taboo']: Dm_Msg += "- " + w + "\n"
        Dm_Msg += "\nStart Giving Clues In The Group Chat Now"
        
        await context.bot.send_message(chat_id=Game_State["Clue_Giver"], text=Dm_Msg)
        
        Announce = "A New Round Has Officially Started For Everyone\n\n"
        Announce += "Selected Clue Giver " + Lobby_Data["Player_Names"][Game_State["Clue_Giver"]] + "\n"
        Announce += "Current Active Team Team " + Game_State["Current_Turn_Team"] + "\n\n"
        Announce += "Secret Details Have Been Sent To The Clue Giver Private DM\n"
        Announce += "All Other Participants Should Start Guessing The Word\n"
        Announce += "The Timer Has Been Activated Good Luck To All"
        await update.message.reply_text(Announce)
        
        asyncio.create_task(Manage_Round_Timer(update.effective_chat.id, context, word_obj["Word"]))
    except Exception:
        await update.message.reply_text("Communication Error Could Not Message The Clue Giver DM")

async def Referee_Logic(update: Update, context):
    if not Game_State["Round_Active"]: return
    user, text = update.message.from_user, update.message.text.lower().strip()

    if user.id == Game_State["Clue_Giver"]:
        for forbidden in Game_State["Taboo_Words"]:
            if forbidden in text:
                Game_State["Round_Active"] = False
                Game_State["Current_Turn_Team"] = "B" if Game_State["Current_Turn_Team"] == "A" else "A"
                Penalty = "Violation Detected A Taboo Word Has Been Spoken\n\n"
                Penalty += "Player Name " + user.first_name + "\n"
                Penalty += "Forbidden Word Used " + forbidden + "\n\n"
                Penalty += "The Turn Has Now Switched Automatically\n"
                Penalty += "Type /Next To Begin The Next Round Immediately"
                await update.message.reply_text(Penalty)
                return
    else:
        if text == Game_State["Current_Word"].lower():
            Game_State["Round_Active"] = False
            team = Game_State["Current_Turn_Team"]
            Game_State["Scores"][team] += 1
            Update_Stats(user.id, user.first_name, pts=10)
            
            Victory = "Fantastic Achievement The Word Has Been Guessed Correctlty\n\n"
            Victory += "Winning Participant Name " + user.first_name + "\n"
            Victory += "Ten Points Awarded To Team " + team + "\n\n"
            Victory += "Great Teamwork Shown By The Players Today\n"
            Victory += "Type /Next To Proceed To The Next Thrilling Round"
            Game_State["Current_Word"] = None
            await update.message.reply_text(Victory)

async def Profile_Handler(update: Update, context):
    Cursor.execute("Select Points, Wins, Games_Played From Players Where User_Id = ?", (update.message.from_user.id,))
    data = Cursor.fetchone()
    if not data: return await update.message.reply_text("No Statistics Found For This Profile In Database")
    
    Profile_Msg = "Your Personal Gaming Profile Statistics Report\n\n"
    Profile_Msg += "Participant Name " + update.message.from_user.first_name + "\n"
    Profile_Msg += "Total Career Points Earned " + str(data[0]) + "\n"
    Profile_Msg += "Total Match Victories Recorded " + str(data[1]) + "\n"
    Profile_Msg += "Total Number Of Games Played " + str(data[2]) + "\n\n"
    Profile_Msg += "Continue Playing To Improve Your Global Ranking Status"
    await update.message.reply_text(Profile_Msg)

async def Leaderboard_Handler(update: Update, context):
    Cursor.execute("Select Name, Points From Players Order By Points Desc Limit 5")
    ranks = Cursor.fetchall()
    Board = "Presenting The Global Hall Of Fame Top Five Players\n\n"
    for i, p in enumerate(ranks): 
        Board += str(i+1) + ". " + p[0] + " With Total Points " + str(p[1]) + "\n"
    Board += "\nCan You Surpass These Legends In The Next Game\n"
    Board += "Keep Playing Regularly To Reach The Top Position"
    await update.message.reply_text(Board)

async def Reset_Handler(update: Update, context):
    global Lobby_Data, Game_State
    Lobby_Data = {"Is_Open": False, "Creator_Id": None, "Players": [], "Player_Names": {}}
    Game_State.update({"Is_Running": False, "Round_Active": False, "Current_Word": None})
    
    Reset_Msg = "The Game Engine Has Been Successfully Reset To Default\n\n"
    Reset_Msg += "All Current Session Data Has Been Wiped Clean\n"
    Reset_Msg += "You May Now Create A New Lobby Using /Lobby Command\n\n"
    Reset_Msg += "Thank You For Using Our Automated Gaming System"
    await update.message.reply_text(Reset_Msg)

async def Status_Handler(update: Update, context):
    if not Game_State["Is_Running"]: 
        return await update.message.reply_text("Information No Active Game Match Is Currently In Progress")
    
    Status_Report = "Presenting The Current Detailed Match Status Report\n\n"
    Status_Report += "Team A Current Score " + str(Game_State["Scores"]["A"]) + " Points\n"
    Status_Report += "Team B Current Score " + str(Game_State["Scores"]["B"]) + " Points\n\n"
    
    # Leader Logic
    if Game_State["Scores"]["A"] > Game_State["Scores"]["B"]:
        Status_Report += "Dominating Team Team A Is Currently Leading The Match\n"
    elif Game_State["Scores"]["B"] > Game_State["Scores"]["A"]:
        Status_Report += "Dominating Team Team B Is Currently Leading The Match\n"
    else:
        Status_Report += "Match Status Both Teams Are Currently On Equal Scores\n"
        
    Status_Report += "\nCurrent Turn Team " + Game_State["Current_Turn_Team"] + "\n"
    
    if Game_State["Round_Active"]:
        Status_Report += "Round Status Active Word Guessing Is Ongoing\n"
        Status_Report += "Current Clue Giver " + Lobby_Data["Player_Names"].get(Game_State["Clue_Giver"], "Unknown") + "\n"
    else:
        Status_Report += "Round Status Waiting For Next Round Initialization\n"
    
    Status_Report += "\nKeep Playing And Perform Better To Secure Your Victory"
    await update.message.reply_text(Status_Report)

def main():
    Token_Val = "8380924465:AAFwbA-55qfkrA0-QJ_AL2uWuuS3Pt7y-Mw"
    Application = ApplicationBuilder().token(Token_Val).connect_timeout(40).read_timeout(40).write_timeout(40).pool_timeout(40).build()
    
    Application.add_handler(CommandHandler("Help", Help_Handler))
    Application.add_handler(CommandHandler("Lobby", Lobby_Handler))
    Application.add_handler(CommandHandler("Join", Join_Handler))
    Application.add_handler(CommandHandler("Start", Start_Handler))
    Application.add_handler(CommandHandler("Next", Next_Round_Handler))
    Application.add_handler(CommandHandler("Status", Status_Handler))
    Application.add_handler(CommandHandler("Profile", Profile_Handler))
    Application.add_handler(CommandHandler("Leaderboard", Leaderboard_Handler))
    Application.add_handler(CommandHandler("Reset", Reset_Handler))
    Application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), Referee_Logic))
    
    print("Taboo Professional Engine Is Live")
    Application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
