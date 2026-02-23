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

# Global State Management
Lobby_Data = {
    "Is_Open": False,
    "Creator_Id": None,
    "Players": [],
    "Player_Names": {}
}

Game_State = {
    "Is_Running": False,
    "Team_Bjp": [],
    "Team_Congress": [],
    "Scores": {"Bjp": 0, "Congress": 0},
    "Current_Turn_Team": "Bjp",
    "Current_Word": None,
    "Taboo_Words": [],
    "Clue_Giver": None,
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
    # Total Time Is Now 5 Minutes Or 300 Seconds
    
    # Phase 1 Wait 60 Seconds Total 1 Minute Passed Remaining 4 Minutes
    await asyncio.sleep(60)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Msg = "⏳ Time Alert Four Minutes Remaining In This Round\n\n"
        Msg += "Keep Guessing The Word To Win Points For Your Team"
        await context.bot.send_message(chat_id=chat_id, text=Msg)

    # Phase 2 Wait 60 Seconds Total 2 Minutes Passed Remaining 3 Minutes
    await asyncio.sleep(60)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Msg = "⏳ Time Alert Three Minutes Remaining For This Word\n\n"
        Msg += "Clue Giver Please Give Some More Hints To Help Your Team"
        await context.bot.send_message(chat_id=chat_id, text=Msg)

    # Phase 3 Wait 60 Seconds Total 3 Minutes Passed Remaining 2 Minutes
    await asyncio.sleep(60)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Msg = "⏳ Time Alert Two Minutes Remaining On The Clock\n\n"
        Msg += "The Competition Between Bjp And Congress Is Getting Tough"
        await context.bot.send_message(chat_id=chat_id, text=Msg)

    # Phase 4 Wait 60 Seconds Total 4 Minutes Passed Remaining 1 Minute
    await asyncio.sleep(60)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Msg = "⏳ Time Alert Only One Minute Remaining Hurry Up\n\n"
        Msg += "This Is Your Last Chance To Score Points In This Turn"
        await context.bot.send_message(chat_id=chat_id, text=Msg)

    # Phase 5 Wait 30 Seconds Total 4 Minutes 30 Seconds Passed Remaining 30 Seconds
    await asyncio.sleep(30)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Msg = "🚨 Critical Alert Only Thirty Seconds Left Now\n\n"
        Msg += "Type Your Best Guesses Fast Before The Round Ends"
        await context.bot.send_message(chat_id=chat_id, text=Msg)

    # Phase 6 Wait 20 Seconds Remaining 10 Seconds
    await asyncio.sleep(20)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        await context.bot.send_message(chat_id=chat_id, text="🎯 Final Ten Seconds Remaining On The Timer")

    # Final Deadly Countdown From 5 To 1
    for Count in [5, 4, 3, 2, 1]:
        await asyncio.sleep(1)
        if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
            await context.bot.send_message(chat_id=chat_id, text="🧨 Final Countdown " + str(Count))

    # Final Time Up Logic
    await asyncio.sleep(1)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Game_State["Round_Active"] = False
        Game_State["Current_Word"] = None
        
        # Turn Shift Logic Between Bjp And Congress
        Old_Team = Game_State["Current_Turn_Team"]
        Game_State["Current_Turn_Team"] = "Congress" if Old_Team == "Bjp" else "Bjp"
        
        Final_Msg = "🛑 Time Up The Round Has Ended Successfully\n\n"
        Final_Msg += "The Correct Secret Word Was " + round_word.upper() + "\n"
        Final_Msg += "No One Guessed It Right So No Points Are Awarded\n\n"
        Final_Msg += "The Turn Has Now Shifted To Team " + Game_State["Current_Turn_Team"] + "\n"
        Final_Msg += "Please Use The Next Command To Start The New Round"
        await context.bot.send_message(chat_id=chat_id, text=Final_Msg)

# Command Handlers
async def Help_Handler(update: Update, context):
    Guide = "🌟 Taboo Master Bot Official Help Menu 🌟\n\n"
    
    Guide += "Please Use The Following Commands To Play The Game Easily\n\n"
    
    Guide += "📍 Match Setup Commands\n\n"
    
    Guide += "1️⃣ /lobby Use This To Create A New Game Room For Your Friends\n"
    Guide += "2️⃣ /register Type This To Enter The Active Game Lobby\n"
    Guide += "3️⃣ /start The Host Can Use This To Begin The Match After Everyone Joins\n"
    Guide += "4️⃣ /members Check The List Of All Players Currently In The Lobby\n"
    Guide += "5️⃣ /cancel Stop The Ongoing Match Immediately If Needed\n"
    Guide += "6️⃣ /reset Fully Clear All Data And Start Everything From Zero\n\n"
    
    Guide += "📍 Match Play Commands\n\n"
    
    Guide += "7️⃣ /round Get Your New Secret Word Inside Your Private DM\n"
    Guide += "8️⃣ /clue The Clue Giver Must Send Hints To The Bot DM Using This\n"
   # Guide += "9️⃣ /hint Get A Small Clue If The Word Is Too Hard To Guess\n"
    Guide += "9️⃣ /turn Find Out If It Is The Turn Of Team Bjp Or Team Congress\n"
    Guide += "🔟 /squad See Who Is In Team Bjp And Who Is In Team Congress\n"
    Guide += "📊 /status Check The Live Score To See Which Team Is Winning\n\n"
    
    Guide += "📍 Your Records\n\n"
    
    Guide += "👤 /profile View Your Personal Points And Total Game Wins\n"
    Guide += "🏆 /leaderboard See The Top Ranked Players On The Global Board\n\n"
    
    Guide += "📝 Important Rules For New Players\n"
    Guide += "The Clue Giver Must Start The Bot In Private DM First\n"
    Guide += "Always Send Your Hints Inside The Private DM Of The Bot\n"
    Guide += "The First Person To Type The Correct Word In Group Wins Ten Points\n\n"
    
    Guide += "🔥 Start Playing Now And Lead Your Team To Victory 🔥"
    
    await update.message.reply_text(Guide)

async def Lobby_Handler(update: Update, context):
    # Security Check To Ensure Lobby Is Created Only In Group Chats
    if update.effective_chat.type == 'private':
        Dm_Error = "🛑 Access Denied You Cannot Create A Game Lobby In Private Messages\n\n"
        Dm_Error += "Please Add This Bot To A Group To Start A New Match\n"
        Dm_Error += "Lobbies Are Only For Multiplayer Games In Groups\n"
        Dm_Error += "Please Try This Command Again Inside A Telegram Group"
        return await update.message.reply_text(Dm_Error)

    # Check If A Lobby Is Already Active
    if Lobby_Data["Is_Open"]: 
        Active_Error = "⚠️ Warning A Game Lobby Is Already Open Right Now\n\n"
        Active_Error += "You Cannot Start Two Lobbies At The Same Time\n"
        Active_Error += "Please Wait For The Match To Finish Or Use The Reset Command\n"
        Active_Error += "The Current Host Is Still Managing The Players In The Room"
        return await update.message.reply_text(Active_Error)

    # Initialize The Lobby Data With Creator Information
    User = update.message.from_user
    Lobby_Data.update({
        "Is_Open": True, 
        "Creator_Id": User.id, 
        "Players": [User.id], 
        "Player_Names": {User.id: User.first_name}
    })
    
    # Simple Invitation Message
    Invite = "🎊 A New Taboo Game Lobby Has Been Successfully Created 🎊\n\n"
    Invite += "👤 Host Name: " + User.first_name + "\n"
    Invite += "📊 Status Waiting For Players To Join The Session\n\n"
    
    Invite += "📝 How To Join The Game Below\n\n"
    Invite += "👉 Type /register To Enter This Game Room Right Now\n"
    Invite += "👉 Type /start Once All Your Friends Are Ready\n"
    Invite += "👉 Type /members To See All The Joined Players\n"
    Invite += "👉 Note You Need At Least Two Players To Start The Match\n\n"
    
    Invite += "🔥 Get Ready For A Fun Battle Of Words And Speed\n"
    Invite += "🌟 Show Everyone That You Are The Smartest Player Here\n"
    Invite += "📢 Tell Your Friends To Join Quickly To Start The Fun\n\n"
    Invite += "🛠️ System Architect: @bhawaniisinghshekhawat"
    
    await update.message.reply_text(Invite)

async def Join_Handler(update: Update, context):
    User = update.message.from_user
    
    # Check If Lobby Is Actually Open
    if not Lobby_Data["Is_Open"]: 
        No_Lobby = "❌ Error No Active Game Lobby Found To Join Right Now\n\n"
        No_Lobby += "Please Ask A Friend To Create A New Lobby First\n"
        No_Lobby += "You Can Use The Lobby Command To Start Your Own Game Room\n"
        No_Lobby += "Make Sure You Are In The Group To Play The Match Together"
        return await update.message.reply_text(No_Lobby)

    # Check If Player Is Already Inside The Lobby
    if User.id in Lobby_Data["Players"]: 
        Already_In = "ℹ️ Info You Are Already A Member Of This Game Lobby\n\n"
        Already_In += "Please Wait For The Host To Start The Official Match\n"
        Already_In += "You Cannot Join The Same Game More Than Once\n"
        Already_In += "Check The Member List To See Your Name In The Roster"
        return await update.message.reply_text(Already_In)

    # Security Check To Verify If User Has Started The Bot In Private DM
    try:
        # Checking If Bot Can Communicate With User
        await context.bot.send_chat_action(chat_id=User.id, action="typing")
    except Exception:
        # If Failed It Means The User Has Not Started The Bot In DM
        Dm_Needed = "⚠️ Action Required Please Start The Bot In Private DM First ⚠️\n\n"
        Dm_Needed += "Hello " + User.first_name + " The System Cannot Send You Secret Words Yet\n"
        Dm_Needed += "Please Click On The Bot Name And Press The Start Button In Private\n"
        Dm_Needed += "After Starting The Bot Come Back Here And Type Join Again\n"
        Dm_Needed += "This Step Is Required So You Can Receive Your Hidden Words Later"
        return await update.message.reply_text(Dm_Needed)

    # If All Checks Pass Add The User To The Lobby
    Lobby_Data["Players"].append(User.id)
    Lobby_Data["Player_Names"][User.id] = User.first_name
    
    Success_Msg = "✅ " + User.first_name + " Has Successfully Joined The Game Lobby\n\n"
    Success_Msg += "📊 Current Total Player Count Is Now " + str(len(Lobby_Data["Players"])) + " Active Members\n"
    Success_Msg += "🕒 We Are Still Waiting For More Friends To Join The Fun\n\n"
    Success_Msg += "📢 Invite Your Group Members To Join The Game Right Now\n"
    Success_Msg += "🚀 The Match Will Be Ready To Start Once Everyone Is Here\n"
    Success_Msg += "💎 Get Ready To Play The Most Fun Taboo Game Today"
    
    await update.message.reply_text(Success_Msg)

async def Start_Handler(update: Update, context):
    # Check If The Match Is Already Running Or Lobby Is Not Created
    if not Lobby_Data["Is_Open"]:
        return await update.message.reply_text("❌ Error There Is No Active Lobby To Start At This Moment")

    # Only The Person Who Created The Lobby Can Start The Match
    if update.message.from_user.id != Lobby_Data["Creator_Id"]:
        No_Permission = "🚫 Access Denied Only The Host Can Start The Match 🚫\n\n"
        No_Permission += "Please Ask The Host " + Lobby_Data["Player_Names"][Lobby_Data["Creator_Id"]] + " To Start The Game\n"
        No_Permission += "Only The Person Who Created This Lobby Can Start Forming Teams\n"
        No_Permission += "This Rule Makes Sure Everyone Is Ready Before The Game Begins Today"
        return await update.message.reply_text(No_Permission)

    # Verification For Minimum Players
    Total_Players = len(Lobby_Data["Players"])
    if Total_Players < 2:
        return await update.message.reply_text("⚠️ Not Enough Players You Need At Least Two Players To Make Teams")

    # Team Balancing Logic
    if Total_Players % 2 != 0:
        Balancing_Error = "⚖️ Team Balance Warning You Need An Even Number Of Players For A Fair Match\n\n"
        Balancing_Error += "Current Total Player Count Is " + str(Total_Players) + " Which Means Teams Will Be Unequal\n"
        Balancing_Error += "Please Ask One More Friend To Join So Both Teams Have Equal Players\n"
        Balancing_Error += "We Want Fair Play For Both Team Bjp And Team Congress Members\n"
        Balancing_Error += "Once The Player Count Is Even You Can Start The Game Easily"
        return await update.message.reply_text(Balancing_Error)

    # Shuffle And Divide Teams Into Bjp And Congress
    random.shuffle(Lobby_Data["Players"])
    mid = Total_Players // 2
    Game_State.update({
        "Is_Running": True, 
        "Team_Bjp": Lobby_Data["Players"][:mid], 
        "Team_Congress": Lobby_Data["Players"][mid:], 
        "Scores": {"Bjp": 0, "Congress": 0},
        "Current_Turn_Team": "Bjp"
    })
    Lobby_Data["Is_Open"] = False
    
    # Simple Announcement Of Team Formation
    Battle_Msg = "⚔️ The Taboo Battle Has Started And Teams Are Now Ready ⚔️\n\n"
    
    Battle_Msg += "🪷 Participate Members Of Team BJP:\n"
    for p_id in Game_State["Team_Bjp"]: 
        Battle_Msg += "✨ " + Lobby_Data["Player_Names"][p_id] + "\n"
    
    Battle_Msg += "\n🪬 Participate Members Of Team Congress:\n"
    for p_id in Game_State["Team_Congress"]: 
        Battle_Msg += "✨ " + Lobby_Data["Player_Names"][p_id] + "\n"
    
    Battle_Msg += "\n📝 Simple Match Instructions For Both Teams Below\n\n"
    Battle_Msg += "👉 We Are Starting The First Round With Team Bjp Now\n"
    Battle_Msg += "👉 Please Type The Round Command To Get Your First Secret Word In DM\n"
    Battle_Msg += "👉 Clue Givers Must Check Their Private DM Before Giving Hints In The Group\n\n"
    
    Battle_Msg += "🔥 May The Smartest And Fastest Team Win The Game Today 🔥\n\n"
    Battle_Msg += "🛠️ System Architect: @bhawaniisinghshekhawat"
    
    await update.message.reply_text(Battle_Msg)

async def Next_Round_Handler(update: Update, context):
    # Ensure Global Declaration Is At The Absolute Top To Avoid Errors
    global Game_State, Lobby_Data

    if not Game_State["Is_Running"]: 
        Invalid_Match = "🚫 Error There Is No Active Match Running Right Now\n\n"
        Invalid_Match += "Please Make Sure You Have Created A Lobby And Started The Game\n"
        Invalid_Match += "Use The Lobby Command To Host A New Room And Join Your Friends\n"
        Invalid_Match += "Once Teams Are Ready You Can Use This Command To Start The Round"
        return await update.message.reply_text(Invalid_Match)

    if Game_State["Round_Active"]:
        Busy_Error = "⚠️ Warning A Round Is Already Going On In This Group\n\n"
        Busy_Error += "You Cannot Get A New Word Until The Current Timer Ends\n"
        Busy_Error += "Please Focus On The Current Secret Word And Give Good Hints\n"
        Busy_Error += "Wait For The Current Turn To Finish Before Starting The Next One"
        return await update.message.reply_text(Busy_Error)

    # Dynamic Team Key For Bjp And Congress
    Team_Key = "Team_" + Game_State["Current_Turn_Team"]
    Current_Team_Roster = Game_State[Team_Key]
    Game_State["Clue_Giver"] = random.choice(Current_Team_Roster)
    
    # Pick A Random Word
    Word_Obj = random.choice(Word_Library)
    
    Game_State.update({
        "Current_Word": Word_Obj["Word"],
        "Taboo_Words": [W.lower() for W in Word_Obj["Taboo"]],
        "Round_Active": True
    })

    try:
        # Simple Private Message For Clue Giver
        Dm_Msg = "🤫 Your Secret Taboo Word Details Are Here 🤫\n\n"
        Dm_Msg += "🎯 Your Secret Word Is: " + Word_Obj['Word'].upper() + "\n\n"
        Dm_Msg += "🚫 Do Not Use These Taboo Words Or Your Turn Will End\n"
        for W in Word_Obj['Taboo']: Dm_Msg += "✨ " + W + "\n"
        Dm_Msg += "\n📝 Instructions Use The Clue Command In This DM To Send Hints\n"
        Dm_Msg += "🚀 Example Type Clue It Is A Very Famous Indian Snack\n"
        Dm_Msg += "🔥 Good Luck Make Your Team Guess As Fast As Possible"
        
        await context.bot.send_message(chat_id=Game_State["Clue_Giver"], text=Dm_Msg)
        
        # Simple Group Announcement
        Announce = "🔔 A New Exciting Round Has Started For Everyone 🔔\n\n"
        Announce += "👤 Clue Giver For This Round Is " + Lobby_Data["Player_Names"][Game_State["Clue_Giver"]] + "\n"
        Announce += "🚩 Playing Team Is Team " + Game_State["Current_Turn_Team"] + "\n\n"
        Announce += "📥 The Secret Word Has Been Sent To The Clue Giver Private DM\n"
        Announce += "⏳ The Game Timer Of Five Minutes Is Now Active\n"
        Announce += "📢 Team Members Should Start Typing Their Guesses In This Group\n"
        Announce += "🌟 Use Your Brain To Win Ten Points For Your Team"
        await update.message.reply_text(Announce)
        
        # Start The 5 Minute Timer Task
        asyncio.create_task(Manage_Round_Timer(update.effective_chat.id, context, Word_Obj["Word"]))
        
    except Exception:
        # Error If Bot Cannot DM The Player
        Fail_Msg = "❌ Error Could Not Deliver The Secret Message ❌\n\n"
        Fail_Msg += "It Seems The Player " + Lobby_Data["Player_Names"][Game_State["Clue_Giver"]] + " Has Not Started The Bot\n"
        Fail_Msg += "Please Make Sure You Have Started The Bot In Private DM To Get Words\n"
        Fail_Msg += "This Round Is Being Cancelled Please Try The Command Again"
        Game_State["Round_Active"] = False
        await update.message.reply_text(Fail_Msg)
        
# 1. New Handler For Receiving Clues In Private DM
async def Clue_Submit_Handler(update: Update, context):
    # Ensure This Command Is Only Used Inside Private Chat
    if update.effective_chat.type != 'private':
        return 

    User = update.message.from_user
    
    # Check If The Round Is Active And User Is The Assigned Clue Giver
    if not Game_State["Round_Active"] or User.id != Game_State["Clue_Giver"]:
        Error_Dm = "🚫 Access Denied You Cannot Submit Clues Right Now\n\n"
        Error_Dm += "Please Wait For Your Official Turn To Give Hints To Your Team\n"
        Error_Dm += "Only The Player Who Got The Secret Word Can Use This Command\n"
        Error_Dm += "Check The Group Chat To See Whose Turn Is Going On Currently"
        return await update.message.reply_text(Error_Dm)

    # Validate If Clue Content Is Provided
    Clue_Text = " ".join(context.args)
    if not Clue_Text:
        Usage_Dm = "📝 Instruction Please Type Your Hint After The Command\n\n"
        Usage_Dm += "Example Usage Format Type Clue It Is Very Famous In India\n"
        Usage_Dm += "Your Hint Will Be Sent To The Group Automatically For Everyone\n"
        Usage_Dm += "Make Sure Your Description Does Not Use Any Forbidden Words"
        return await update.message.reply_text(Usage_Dm)

    # Check For Forbidden Taboo Words Inside The Submitted Clue
    for Forbidden in Game_State["Taboo_Words"]:
        if Forbidden in Clue_Text.lower():
            Violation_Dm = "⚠️ Forbidden Word Found Your Hint Has A Restricted Word\n\n"
            Violation_Dm += "Taboo Word Used " + Forbidden.upper() + "\n"
            Violation_Dm += "Please Write Your Hint Again Without Using This Word\n"
            Violation_Dm += "Be Careful Because Using Forbidden Words Is Against The Rules"
            return await update.message.reply_text(Violation_Dm)

    # Forward The Clue To The Main Group Chat
    Group_Id = context.bot_data.get("Current_Group_Id")
    if Group_Id:
        Forward_Msg = "📣 Attention Everyone A New Hint Has Arrived From The Clue Giver 📣\n\n"
        Forward_Msg += "💡 Hint Message: " + Clue_Text.upper() + "\n\n"
        Forward_Msg += "🔎 All Players Should Read This Hint And Type Their Guesses Now\n"
        Forward_Msg += "🕒 The Timer Is Running Fast So Give Your Best Answers Quickly\n"
        Forward_Msg += "🏆 The First Person To Guess Correct Wins Ten Points For Their Team\n\n"
        Forward_Msg += "🛠️ System Architect: @bhawaniisinghshekhawat"
        await context.bot.send_message(chat_id=Group_Id, text=Forward_Msg)
        await update.message.reply_text("✅ Success Your Hint Has Been Sent To The Group Chat Successfully")

# 2. Updated Referee Logic For Handling Guesses In Group Chat
async def Referee_Logic(update: Update, context):
    # Only Process Text Messages Inside The Group Chat
    if update.effective_chat.type == 'private': return
    if not Game_State["Round_Active"]: return
    
    User = update.message.from_user
    Text_Guess = update.message.text.lower().strip()
    
    # Save Group Id Dynamically For Forwarding Clues Later
    context.bot_data["Current_Group_Id"] = update.effective_chat.id

    # If The Clue Giver Types The Forbidden Word In Group Chat By Mistake
    if User.id == Game_State["Clue_Giver"]:
        for Forbidden in Game_State["Taboo_Words"]:
            if Forbidden in Text_Guess:
                Game_State["Round_Active"] = False
                Game_State["Current_Word"] = None
                
                # Turn Shift Logic Between Bjp And Congress
                Old_Team = Game_State["Current_Turn_Team"]
                Game_State["Current_Turn_Team"] = "Congress" if Old_Team == "Bjp" else "Bjp"
                
                Penalty_Msg = "🚫 Major Penalty The Clue Giver Used A Forbidden Word In Public 🚫\n\n"
                Penalty_Msg += "Player Name " + User.first_name + "\n"
                Penalty_Msg += "Forbidden Word Used " + Forbidden.upper() + "\n\n"
                Penalty_Msg += "This Round Has Ended And The Turn Has Changed To The Other Team\n"
                Penalty_Msg += "Please Type The Round Command To Start A New Turn For Your Team\n"
                Penalty_Msg += "Please Follow The Rules To Keep The Game Fair For Everyone"
                await update.message.reply_text(Penalty_Msg)
                return
    else:
        # Check If A Participant Guessed The Correct Secret Word
        if Text_Guess == Game_State["Current_Word"].lower():
            Game_State["Round_Active"] = False
            Winning_Team = Game_State["Current_Turn_Team"]
            Game_State["Scores"][Winning_Team] += 1
            
            # Update Statistics In Database
            Update_Stats(User.id, User.first_name, pts=10)
            
            Victory_Msg = "🎊 Great Job The Secret Word Has Been Guessed Successfully 🎊\n\n"
            Victory_Msg += "👑 Winner Name " + User.first_name + "\n"
            Victory_Msg += "🎯 Correct Answer Was " + Game_State["Current_Word"].upper() + "\n"
            Victory_Msg += "📈 Ten Points Have Been Awarded To Team " + Winning_Team + "\n\n"
            Victory_Msg += "You Are Doing Great Work And Thinking Very Fast Today\n"
            Victory_Msg += "Please Type The Round Command To Start The Next Exciting Round\n"
            Victory_Msg += "Keep Playing Well To Reach The Top Of The Leaderboard\n\n"
            Victory_Msg += "🛠️ System Architect: @bhawaniisinghshekhawat"
            
            Game_State["Current_Word"] = None
            await update.message.reply_text(Victory_Msg)

async def Profile_Handler(update: Update, context):
    # Fetch Player Statistics From The Database
    Cursor.execute("Select Points, Wins, Games_Played From Players Where User_Id = ?", (update.message.from_user.id,))
    Data = Cursor.fetchone()
    
    # Check If The Player Has Any Record
    if not Data: 
        No_Record = "🔍 No Record Found For Your Profile In Our Database\n\n"
        No_Record += "It Looks Like You Have Not Played Any Taboo Matches Yet\n"
        No_Record += "Please Join A Lobby And Play A Match To Create Your Record\n"
        No_Record += "Your Progress Will Be Tracked Once You Start Winning Points\n"
        No_Record += "We Hope To See Your Name On Our Leaderboard Very Soon"
        return await update.message.reply_text(No_Record)
    
    # Extract Values For Calculation
    Points = Data[0]
    Wins = Data[1]
    Total_Games = Data[2]
    
    # Calculate Win Rate Percentage
    Win_Rate = (Wins / Total_Games) * 100 if Total_Games > 0 else 0
    
    # Determine Player Level Based On Points
    Player_Tier = "New Player"
    if Points > 500: Player_Tier = "Smart Player"
    if Points > 1500: Player_Tier = "Expert Master"
    if Points > 5000: Player_Tier = "Grand Champion"

    # Constructing The Simple Profile Report
    Profile_Msg = "🛡️ Your Official Gaming Profile Statistics 🛡️\n\n"
    
    Profile_Msg += "👤 Player Name: " + update.message.from_user.first_name + "\n"
    Profile_Msg += "🎖️ Current Level Status: " + Player_Tier + "\n\n"
    
    Profile_Msg += "📊 Your Performance Details Below\n\n"
    
    Profile_Msg += "💎 Total Career Points Scored: " + str(Points) + " Points\n"
    Profile_Msg += "🏆 Total Match Wins Recorded: " + str(Wins) + " Wins\n"
    Profile_Msg += "🎮 Total Games Played: " + str(Total_Games) + " Matches\n"
    Profile_Msg += "📈 Overall Winning Chance: " + str(round(Win_Rate, 2)) + " Percent\n\n"
    
    Profile_Msg += "📝 Helpful Advice For You\n"
    Profile_Msg += "You Are Now In The " + Player_Tier + " Category Based On Your Performance\n"
    Profile_Msg += "Play More Rounds Regularly To Improve Your Winning Percentage\n"
    Profile_Msg += "Keep Winning To Reach The Grand Champion Status Quickly\n\n"
    
    Profile_Msg += "🌟 Keep Playing To Become A Legend In Our Global Hall Of Fame 🌟"
    
    await update.message.reply_text(Profile_Msg)

async def Leaderboard_Handler(update: Update, context):
    # Fetch Top Ten Players For The Board
    Cursor.execute("Select Name, Points From Players Order By Points Desc Limit 10")
    Ranks = Cursor.fetchall()
    
    # Check If The Leaderboard Has Any Data
    if not Ranks:
        Empty_Board = "📭 Alert The Global Leaderboard Is Currently Empty\n\n"
        Empty_Board += "It Seems No Players Have Scored Any Points In This Season Yet\n"
        Empty_Board += "Be The First Player To Win A Match And Take The Top Rank Here\n"
        Empty_Board += "Start A New Game Lobby Now To Begin Your Journey To Become A Legend"
        return await update.message.reply_text(Empty_Board)
    
    # Constructing The Simple Hall Of Fame Board
    Board = "🏆 The Official Taboo Global Hall Of Fame Top Rankings 🏆\n\n"
    Board += "See The Smartest And Fastest Thinkers In Our Game Community Today\n\n"
    
    for Index, Player in enumerate(Ranks):
        Position = Index + 1
        Player_Name = Player[0]
        Player_Points = Player[1]
        
        # Assigning Simple Rank Titles For Top Three Positions
        if Position == 1:
            Rank_Icon = "🥇 First Place"
        elif Position == 2:
            Rank_Icon = "🥈 Second Place"
        elif Position == 3:
            Rank_Icon = "🥉 Third Place"
        else:
            Rank_Icon = "🏅 Position " + str(Position)
            
        Board += Rank_Icon + " Player Name " + Player_Name + " With Total Career Points " + str(Player_Points) + "\n"
    
    Board += "\n📊 Global Ranking Summary And Match Status\n"
    Board += "The Fight For The Top Rank Is Getting Very Hard This Season\n"
    Board += "Do You Have The Speed To Beat These Great Players On The Board\n"
    Board += "Every Correct Guess Helps You Get Closer To The Gold Medal Status\n\n"
    
    Board += "✨ Keep Playing Regularly To Save Your Name On This Famous Board ✨"
    
    await update.message.reply_text(Board)

# Function To Show Current Lobby Members
async def Members_Handler(update: Update, context):
    if not Lobby_Data["Players"]:
        return await update.message.reply_text("🔍 System Alert The Lobby Is Empty With No Players Right Now")
    
    Member_List = "👥 List Of Players Currently In The Game Lobby 👥\n\n"
    for P_Id in Lobby_Data["Players"]:
        Member_List += "✨ Player Name " + Lobby_Data["Player_Names"][P_Id] + "\n"
    
    Member_List += "\n📊 Total Number Of Players Waiting To Play " + str(len(Lobby_Data["Players"]))
    await update.message.reply_text(Member_List)

async def Team_Handler(update: Update, context):
    if not Game_State["Is_Running"]:
        return await update.message.reply_text("🚫 Error Teams Are Not Formed Until The Match Starts")
    
    Team_Msg = "⚔️ Official Player List For Both Teams ⚔️\n\n"
    Team_Msg += "🪷 Members Of Team BJP:\n"
    for P_Id in Game_State["Team_Bjp"]: Team_Msg += "✨ " + Lobby_Data["Player_Names"][P_Id] + "\n"
    
    Team_Msg += "\n🪬 Members Of Team Congress:\n"
    for P_Id in Game_State["Team_Congress"]: Team_Msg += "✨ " + Lobby_Data["Player_Names"][P_Id] + "\n"
    
    await update.message.reply_text(Team_Msg)

async def Hint_Handler(update: Update, context):
    if not Game_State["Round_Active"]:
        return await update.message.reply_text("🚫 System Alert There Is No Active Round To Give A Hint")
    
    Secret = Game_State["Current_Word"]
    # Generates A Simple Masked Hint
    Masked = Secret[0] + " " + " ".join(["_" for _ in range(len(Secret)-1)])
    
    Hint_Msg = "💡 New System Hint For The Secret Word 💡\n\n"
    Hint_Msg += "🔎 Word Starting Letter: " + Masked.upper() + "\n"
    Hint_Msg += "📏 Total Number Of Letters In The Word: " + str(len(Secret)) + "\n\n"
    Hint_Msg += "📢 Everyone Please Use This Hint To Guess The Word Correctly"
    await update.message.reply_text(Hint_Msg)

async def Turn_Handler(update: Update, context):
    if not Game_State["Is_Running"]:
        return await update.message.reply_text("🔍 Match Status The Game Has Not Started Yet")
    
    # Using Your New Team Names
    Team_Name = "Team Bjp" if Game_State["Current_Turn_Team"] == "Bjp" else "Team Congress"
    
    Turn_Report = "🔄 Official Turn Details 🔄\n\n"
    Turn_Report += "🚩 Current Turn Is For: " + Team_Name + "\n"
    
    if Game_State["Round_Active"]:
        Turn_Report += "👤 Current Clue Giver Is: " + Lobby_Data["Player_Names"][Game_State["Clue_Giver"]] + "\n"
        Turn_Report += "🕒 The Clock Is Running Please Hurry Up\n"
    else:
        Turn_Report += "🕒 Status Waiting For Someone To Type The Round Command\n"
    
    await update.message.reply_text(Turn_Report)

async def Reset_Handler(update: Update, context):
    # Accessing Global Variables To Clear All Data
    global Lobby_Data, Game_State
    
    # Fully Resetting The Lobby Information To Empty State
    Lobby_Data.update({
        "Is_Open": False, 
        "Creator_Id": None, 
        "Players": [], 
        "Player_Names": {}
    })
    
    # Fully Resetting The Game State For Bjp And Congress Teams
    Game_State.update({
        "Is_Running": False, 
        "Team_Bjp": [], 
        "Team_Congress": [], 
        "Scores": {"Bjp": 0, "Congress": 0},
        "Current_Turn_Team": "Bjp", 
        "Current_Word": None, 
        "Taboo_Words": [], 
        "Clue_Giver": None, 
        "Round_Active": False
    })
    
    # Simple Reset Announcement Message
    Reset_Msg = "🔄 The Taboo Game System Has Been Successfully Reset 🔄\n\n"
    
    Reset_Msg += "🧹 All Current Game Data And Match Scores Have Been Deleted\n"
    Reset_Msg += "🛡️ The System Memory Is Now Clean And Back To Normal Settings\n"
    Reset_Msg += "👤 Any Active Lobby Or Round Has Been Stopped Right Now\n\n"
    
    Reset_Msg += "📝 How To Start A New Game Again\n"
    Reset_Msg += "You Can Now Create A New Game Room Using The Lobby Command\n"
    Reset_Msg += "Make Sure All Your Friends Are Ready To Join The Teams Again\n"
    Reset_Msg += "Old Scores From The Last Game Are Now Removed From The System\n\n"
    
    Reset_Msg += "🌟 Thank You For Using Our Gaming Management System 🌟"
    
    await update.message.reply_text(Reset_Msg)

async def Status_Handler(update: Update, context):
    # Verification Check If The Game Is Actually Active
    if not Game_State["Is_Running"]: 
        No_Game = "🔍 Info There Is No Active Taboo Match Going On Right Now\n\n"
        No_Game += "There Are No Scores To Show Because The Game Has Not Started\n"
        No_Game += "Please Use The Lobby Command To Create A New Game First\n"
        No_Game += "Once The Match Begins You Can Use Status To Track Your Score"
        return await update.message.reply_text(No_Game)
    
    # Constructing The Simple Status Report Header
    Status_Report = "📊 The Current Live Match Score And Status Report 📊\n\n"
    
    # Score Display For Bjp And Congress
    Score_Bjp = Game_State["Scores"]["Bjp"]
    Score_Congress = Game_State["Scores"]["Congress"]
    
    Status_Report += "🟦 Team BJP Current Total Score: " + str(Score_Bjp) + " Points\n"
    Status_Report += "🟥 Team Congress Current Total Score: " + str(Score_Congress) + " Points\n\n"
    
    # Simple Leadership Status
    Status_Report += "🏆 Who Is Winning Right Now\n"
    if Score_Bjp > Score_Congress:
        Difference = Score_Bjp - Score_Congress
        Status_Report += "Current Leader Team Bjp Is Leading By " + str(Difference) + " Points\n"
    elif Score_Congress > Score_Bjp:
        Difference = Score_Congress - Score_Bjp
        Status_Report += "Current Leader Team Congress Is Leading By " + str(Difference) + " Points\n"
    else:
        Status_Report += "Match Status Both Teams Currently Have The Same Score\n"
        
    # Current Turn And Round Details
    Status_Report += "\n🎮 Current Turn Details\n"
    Current_Team_Name = "Team Bjp" if Game_State["Current_Turn_Team"] == "Bjp" else "Team Congress"
    Status_Report += "Playing Right Now " + Current_Team_Name + "\n"
    
    if Game_State["Round_Active"]:
        Clue_Giver_Name = Lobby_Data["Player_Names"].get(Game_State["Clue_Giver"], "Unknown Player")
        Status_Report += "Round Status The Word Guessing Is Going On Right Now\n"
        Status_Report += "Clue Giver Name: " + Clue_Giver_Name + "\n"
        Status_Report += "Timer Status The Clock Is Running Down Very Fast\n"
    else:
        Status_Report += "Round Status Waiting For The Next Secret Word To Start\n"
        Status_Report += "Instruction Please Type The Round Command To Start The Next Turn\n"
    
    Status_Report += "\n✨ Keep Playing Well To Lead Your Team To Victory ✨"
    
    await update.message.reply_text(Status_Report)

async def Guide_Handler(update: Update, context):
    Guide_Text = "📖 Official Taboo Game Guide For New Players 📖\n\n"
    
    Guide_Text += "If You Are New To This Game This Guide Will Help You Become A Pro\n\n"
    
    Guide_Text += "📍 Step 1 How To Join The Game\n"
    Guide_Text += "First Click On The Bot Name And Press The Start Button In Private DM\n"
    Guide_Text += "Then Come Back To The Group And Type Join To Enter The Match\n"
    Guide_Text += "The Game Starts Only When Teams Are Balanced So Invite Your Friends\n\n"
    
    Guide_Text += "📍 Step 2 Role Of The Clue Giver\n"
    Guide_Text += "In Every Round One Player Will Be Chosen As The Clue Giver\n"
    Guide_Text += "The Bot Will Send You A Secret Word And Five Forbidden Words In Private\n"
    Guide_Text += "You Must Explain The Secret Word Without Using Any Of Those Forbidden Words\n"
    Guide_Text += "To Give A Hint Type Clue Followed By Your Message In Bot DM Like Clue It Is Yellow\n\n"
    
    Guide_Text += "📍 Step 3 How To Guess The Word\n"
    Guide_Text += "Other Players Must Type The Answer Directly In The Group Chat\n"
    Guide_Text += "You Do Not Need Any Command To Guess Just Type The Word Like Mango Or Apple\n"
    Guide_Text += "The First Person To Guess Correctly Wins Ten Points For Their Team\n\n"
    
    Guide_Text += "📍 Step 4 How To Avoid Penalties\n"
    Guide_Text += "The Clue Giver Should Never Type Hints Directly In The Group Chat\n"
    Guide_Text += "If The Clue Giver Uses A Forbidden Word The Round Will End Immediately\n"
    Guide_Text += "Always Watch The Timer Because The Round Ends Automatically After Five Minutes\n\n"
    
    Guide_Text += "📍 Simple Example For You\n"
    Guide_Text += "If The Secret Word Is Samosa And The Forbidden Word Is Potato\n"
    Guide_Text += "You Can Type Clue It Is A Fried Indian Snack In Triangle Shape\n"
    Guide_Text += "You Cannot Use The Word Potato Or You Will Get A Penalty\n\n"
    
    Guide_Text += "🌟 That Is All You Need To Know Now Start Playing And Have Fun 🌟"
    
    await update.message.reply_text(Guide_Text)

async def Rules_Handler(update: Update, context):
    Summary = "🎮 Welcome To The Official Taboo Game Rules Guide 🎮\n\n"
    
    Summary += "This Game Is A Fun Battle Of Words And Quick Thinking Between Team Bjp And Team Congress\n\n"
    
    Summary += "📍 Phase One Creating The Lobby And Making Teams\n"
    Summary += "One Player Must Create A Lobby Using The Lobby Command Inside The Group Chat\n"
    Summary += "Other Players Must Join The Game By Using The Join Command To Register Themselves\n"
    Summary += "The Host Will Start The Match Once Players Are Divided Into Team Bjp And Team Congress\n\n"
    
    Summary += "📍 Phase Two The Secret Word And Giving Hints\n"
    Summary += "In Every Round One Player Will Be Chosen As The Clue Giver For Their Team\n"
    Summary += "The Bot Will Send A Secret Word And Five Forbidden Taboo Words To Your Private DM\n"
    Summary += "The Clue Giver Must Explain The Word Without Using Any Of Those Forbidden Words\n"
    Summary += "Important Note Hints Must Be Sent Only In The Bot Private DM Using The Clue Command\n\n"
    
    Summary += "📍 Phase Three Guessing And Winning Points\n"
    Summary += "Once The Hint Is Sent To The Group All Other Members Must Start Guessing The Word\n"
    Summary += "Players Should Type Their Guesses Directly In The Group Without Using Any Commands\n"
    Summary += "The First Person To Type The Correct Word Wins Ten Points For Their Team Right Away\n"
    Summary += "If The Clue Giver Uses A Forbidden Word The Turn Ends And No Points Are Given\n\n"
    
    Summary += "📍 Phase Four The Game Timer And Winning\n"
    Summary += "Each Round Has A Five Minute Timer With Multiple Time Alerts In The Group\n"
    Summary += "If No One Guesses The Correct Word In Time The Round Ends And The Turn Changes\n"
    Summary += "Players Can Check Their Records Using The Profile And Global Leaderboard Commands\n\n"
    
    Summary += "🌟 Follow These Simple Rules To Play Fair And Become A Grand Champion 🌟"
    
    await update.message.reply_text(Summary)

async def Cancel_Handler(update: Update, context):
    # Professional Global Declaration Must Be The Very First Line
    global Lobby_Data, Game_State

    # Now We Can Safely Check If There Is Actually Anything To Cancel
    if not Lobby_Data["Is_Open"] and not Game_State["Is_Running"]:
        Empty_Error = "❌ Error There Is No Active Lobby Or Match To Cancel ❌\n\n"
        Empty_Error += "The Game System Is Already Stopped Right Now\n"
        Empty_Error += "You Can Create A New Game By Using The Lobby Command Anytime\n"
        Empty_Error += "No Game Data Is Currently Being Used In The System Memory"
        return await update.message.reply_text(Empty_Error)

    # Security Check Only The Host Can Cancel
    User_Id = update.message.from_user.id
    if User_Id != Lobby_Data["Creator_Id"]:
        No_Auth = "🚫 Access Denied Only The Host Can Cancel This Match 🚫\n\n"
        No_Auth += "Player Name " + update.message.from_user.first_name + " Does Not Have Permission\n"
        No_Auth += "Please Ask The Lobby Creator To Stop The Game Properly\n"
        No_Auth += "This Rule Prevents Other Players From Stopping Your Active Game"
        return await update.message.reply_text(No_Auth)

    # Performing The Full System Reset For Cancellation
    Lobby_Data = {"Is_Open": False, "Creator_Id": None, "Players": [], "Player_Names": {}}
    Game_State.update({
        "Is_Running": False, 
        "Round_Active": False, 
        "Current_Word": None, 
        "Team_Bjp": [], 
        "Team_Congress": [], 
        "Scores": {"Bjp": 0, "Congress": 0}
    })
    
    Termination_Msg = "🛑 Official Match Cancellation Notice 🛑\n\n"
    Termination_Msg += "The Current Game Session Has Been Stopped By The Host\n"
    Termination_Msg += "All Active Rounds Scores And Teams Have Been Deleted\n"
    Termination_Msg += "The Bot Memory Is Now Back To Normal Settings Again\n\n"
    
    Termination_Msg += "📝 Information For All Players Below\n"
    Termination_Msg += "You Are Now Free To Start A New Game Using The Lobby Command\n"
    Termination_Msg += "We Hope To See You Back In The Game Very Soon\n\n"
    
    Termination_Msg += "🌟 Thank You For Using Our Taboo Game Management System 🌟\n\n"
    Termination_Msg += "🛠️ System Architect: @bhawaniisinghshekhawat"
    
    await update.message.reply_text(Termination_Msg)

async def Broadcast(update: Update, context):
    Allowed_Username = "bhawaniisinghshekhawat"
    Current_User = update.effective_user.username
    
    # Check If The User Is The Bot Owner
    if not Current_User or Current_User.lower() != Allowed_Username.lower():
        Denied_Msg = "🚫 Access Denied Only The Bot Owner Can Use This Command 🚫\n\n"
        Denied_Msg += "This Is A Restricted Command For Security Reasons\n"
        Denied_Msg += "Your Attempt Has Been Logged In The System"
        return await update.message.reply_text(Denied_Msg)
      
    # Check If Message Content Is Provided
    if not context.args:
        Usage_Msg = "📝 How To Use Broadcast Command 📝\n\n"
        Usage_Msg += "Format Type /Broadcast Your Message Here\n"
        Usage_Msg += "Note Use /n If You Want To Start A New Line\n"
        Usage_Msg += "Example /Broadcast Hello Everyone /n This Is A New Game Update"
        return await update.message.reply_text(Usage_Msg)
      
    Raw_Msg = " ".join(context.args)
    Formatted_Msg = Raw_Msg.replace("/n", "\n")
    
    # Save Message Temporarily
    context.user_data['Pending_Broadcast'] = Formatted_Msg
    
    # Get All Chat Ids From Database And Active Games
    try:
        Broadcast_Data = Collection.find_one({"_id": "Broadcast_List"})
    except:
        Broadcast_Data = None
    
    Total_Chats = list(Broadcast_Data["Chat_Ids"]) if Broadcast_Data and "Chat_Ids" in Broadcast_Data else []
    
    # Add Active Groups From Your Game State
    for Cid in list(Game_State.keys()):
        if Cid not in Total_Chats: Total_Chats.append(Cid)

    if not Total_Chats:
        return await update.message.reply_text("🚨 Error No Active Groups Found To Send The Message")
      
    # Create Simple Selection Buttons
    Keyboard = []
    Keyboard.append([InlineKeyboardButton("🚀 Send To All Groups", callback_data="bc_all")])
    
    for Chat_Id in Total_Chats:
        try:
            # Try To Get The Group Name
            Chat_Info = await context.bot.get_chat(Chat_Id)
            Title = Chat_Info.title if Chat_Info.title else "Group ID " + str(Chat_Id)
            Keyboard.append([InlineKeyboardButton("📡 " + Title, callback_data="bc_" + str(Chat_Id))])
        except:
            continue

    Reply_Markup = InlineKeyboardMarkup(Keyboard)
    await update.message.reply_text(
        "🎯 Select Target Destination 🎯\n\n"
        "Please Choose Where You Want To Send Your Broadcast Message",
        reply_markup=Reply_Markup
    )

async def Broadcast_Callback(update: Update, context):
    Query = update.callback_query
    await Query.answer()
    
    Data = Query.data
    Msg_To_Send = context.user_data.get('Pending_Broadcast')
    
    if not Msg_To_Send:
        return await Query.edit_message_text("❌ Error The Broadcast Message Has Expired Please Try Again")
      
    Targets = []
    if Data == "bc_all":
        try: 
            Broadcast_Data = Collection.find_one({"_id": "Broadcast_List"})
        except: 
            Broadcast_Data = None
        Targets = list(Broadcast_Data["Chat_Ids"]) if Broadcast_Data and "Chat_Ids" in Broadcast_Data else []
        for Cid in list(Game_State.keys()):
            if Cid not in Targets: Targets.append(Cid)
    else:
        Chat_Id = Data.replace("bc_", "")
        Targets = [Chat_Id]

    Success_Count = 0
    for Tid in Targets:
        try:
            # Avoid Sending To The Storage Document ID
            if Tid == "Broadcast_List": continue
            await context.bot.send_message(chat_id=Tid, text=Msg_To_Send)
            Success_Count += 1
        except: 
            continue
      
    Final_Report = "✅ Broadcast Process Complete Successfully ✅\n\n"
    Final_Report += "🚀 Message Delivered To " + str(Success_Count) + " Groups\n"
    Final_Report += "📊 Status All Signals Have Been Sent Successfully\n\n"
    Final_Report += "⚡ System Link Is Now Disconnected"
    
    await Query.edit_message_text(Final_Report)

def main():
    Token_Val = "8380924465:AAFwbA-55qfkrA0-QJ_AL2uWuuS3Pt7y-Mw"
    Application = ApplicationBuilder().token(Token_Val).connect_timeout(40).read_timeout(40).write_timeout(40).pool_timeout(40).build()
    
    Application.add_handler(CommandHandler("help", Help_Handler))
    Application.add_handler(CommandHandler("lobby", Lobby_Handler))
    Application.add_handler(CommandHandler("register", Join_Handler))
    Application.add_handler(CommandHandler("start", Start_Handler))
    Application.add_handler(CommandHandler("round", Next_Round_Handler))
    Application.add_handler(CommandHandler("cancel", Cancel_Handler))
    Application.add_handler(CommandHandler("status", Status_Handler))
    Application.add_handler(CommandHandler("profile", Profile_Handler))
    Application.add_handler(CommandHandler("leaderboard", Leaderboard_Handler))
    Application.add_handler(CommandHandler("reset", Reset_Handler))
    Application.add_handler(CommandHandler("clue", Clue_Submit_Handler))
    Application.add_handler(CommandHandler("rules", Rules_Handler))
    Application.add_handler(CommandHandler("members", Members_Handler))
    Application.add_handler(CommandHandler("squad", Team_Handler))
    # Application.add_handler(CommandHandler("hint", Hint_Handler))
    Application.add_handler(CommandHandler("turn", Turn_Handler))
    Application.add_handler(CommandHandler("guide", Guide_Handler))
    Application.add_handler(CommandHandler("broadcast", Broadcast))
    Application.add_handler(CallbackQueryHandler(Broadcast_Callback, pattern="^bc_"))
    Application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), Referee_Logic))
    
    print("Taboo Professional Engine Is Live ✨")
    Application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
