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
    # Phase 1 Waiting For 30 Seconds Total Time Passed 30s Remaining 90s
    await asyncio.sleep(30)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Alert_90 = "⏳ Time Alert Only Ninety Seconds Remaining For This Round\n\n"
        Alert_90 += "📢 Clue Giver Please Provide Better Hints To Your Team Members\n"
        Alert_90 += "🚀 Speed Up Your Thinking Process Before The Clock Runs Out\n"
        Alert_90 += "🏆 Points Are Waiting For The Fastest Fingers In The Group"
        await context.bot.send_message(chat_id=chat_id, text=Alert_90)

    # Phase 2 Waiting For Another 30 Seconds Total Time Passed 60s Remaining 60s
    await asyncio.sleep(30)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Alert_60 = "⚠️ Warning Alert Only Sixty Seconds Remaining On The Clock\n\n"
        Alert_60 += "⚡ Half Of Your Allocated Time Has Already Been Consumed\n"
        Alert_60 += "🧠 Use Your Brain Power To Guess The Secret Word Right Now\n"
        Alert_60 += "🔥 The Battle Between Teams Is Getting Extremely Intense"
        await context.bot.send_message(chat_id=chat_id, text=Alert_60)

    # Phase 3 Waiting For Another 30 Seconds Total Time Passed 90s Remaining 30s
    await asyncio.sleep(30)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Alert_30 = "🚨 Critical Alert Only Thirty Seconds Left In This Match\n\n"
        Alert_30 += "😱 The Pressure Is Building Up For Both The Teams Today\n"
        Alert_30 += "🏃 Move Fast And Type Your Guesses Into The Chat Box\n"
        Alert_30 += "💰 This Is Your Final Opportunity To Win This Round"
        await context.bot.send_message(chat_id=chat_id, text=Alert_30)

    # Phase 4 Final 20 Seconds Wait Remaining 10s
    await asyncio.sleep(20)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        await context.bot.send_message(chat_id=chat_id, text="🎯 Final Ten Seconds Remaining Hurry Up Everyone")

    # Final Deadly Countdown From 5 To 1
    Countdown_Ticks = [5, 4, 3, 2, 1]
    for Count in Countdown_Ticks:
        await asyncio.sleep(1)
        if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
            await context.bot.send_message(chat_id=chat_id, text="🧨 Counting Down " + str(Count))

    # Final Time Up Logic
    await asyncio.sleep(1)
    if Game_State["Round_Active"] and Game_State["Current_Word"] == round_word:
        Game_State["Round_Active"] = False
        Game_State["Current_Word"] = None
        Current_Team = Game_State["Current_Turn_Team"]
        Game_State["Current_Turn_Team"] = "B" if Current_Team == "A" else "A"
        
        Final_Msg = "🛑 Round Terminated The Total Time Has Fully Expired\n\n"
        Final_Msg += "✅ The Correct Secret Word Was " + round_word.upper() + "\n"
        Final_Msg += "❌ Unfortunately No Points Were Awarded To Any Team Members\n\n"
        Final_Msg += "🔄 The Turn Has Officially Shifted To The Other Team Now\n"
        Final_Msg += "🆕 Please Type The Next Command To Begin The Following Round\n"
        Final_Msg += "✨ Better Luck To Everyone In The Next Challenge"
        await context.bot.send_message(chat_id=chat_id, text=Final_Msg)

# Command Handlers
async def Help_Handler(update: Update, context):
    Guide = "🌟 Welcome To The Professional Taboo Gaming Bot Help Menu 🌟\n\n"
    
    Guide += "Explore The Available Commands Below To Manage Your Gaming Session Efficiently\n\n"
    
    Guide += "1️⃣ /Lobby Use This Command To Create A New Private Gaming Room For Your Friends\n"
    Guide += "Setting Up A Lobby Is The First Step To Start Your Thrilling Match Journey\n\n"
    
    Guide += "2️⃣ /Join Type This Command To Enter Into An Already Created And Active Lobby\n"
    Guide += "Make Sure You Join Before The Host Starts The Official Match Countdown\n\n"
    
    Guide += "3️⃣ /Start This Command Allows The Creator To Begin The Match Once Teams Are Balanced\n"
    Guide += "Once Activated The Bot Will Randomly Assign Everyone Into Two Competitive Teams\n\n"
    
    Guide += "4️⃣ /Next Fetch Your Brand New Secret Word Directly Inside Your Private Chat Inbox\n"
    Guide += "Only The Current Clue Giver Should Use This Command To Receive The Hidden Word\n\n"
    
    Guide += "5️⃣ /Clue Clue Givers Must Use This Command In The Bot Private DM To Send Hints\n"
    Guide += "Your Provided Hint Will Be Safely Forwarded To The Main Group Chat Automatically\n\n"
    
    Guide += "6️⃣ /Status View The Real Time Scoreboard Details And Current Turn Information\n"
    Guide += "Keep Track Of Which Team Is Leading And Who Needs To Perform Better Now\n\n"
    
    Guide += "7️⃣ /Profile Check Your Personal Statistics Including Career Points And Total Wins\n"
    Guide += "Analyze Your Performance Records To Become The Ultimate Taboo Champion\n\n"
    
    Guide += "8️⃣ /Leaderboard See The Global Ranking Of The Top Five Greatest Players Worldwide\n"
    Guide += "Compete With Others To Secure Your Prestigious Rank On This Famous Board\n\n"
    
    Guide += "9️⃣ /Reset Use This To Terminate The Current Session And Clear All Global Data\n"
    Guide += "This Command Is Useful If You Want To Restart The Match From The Very Beginning\n\n"
    
    Guide += "🎮 Enjoy Your Gaming Experience And Play Fairly To Climb Up The Ranks 🎮"
    
    await update.message.reply_text(Guide)

async def Lobby_Handler(update: Update, context):
    # Security Check To Ensure Lobby Is Created Only In Group Chats
    if update.effective_chat.type == 'private':
        Dm_Error = "🛑 Access Denied You Cannot Create A Gaming Lobby Inside Private Messages\n\n"
        Dm_Error += "Please Add This Bot To A Group Chat To Start A New Match Session\n"
        Dm_Error += "Lobbies Are Designed For Multiplayer Experience Only In Public Groups\n"
        Dm_Error += "Try Again By Using This Command Inside Your Preferred Telegram Group"
        return await update.message.reply_text(Dm_Error)

    # Check If A Lobby Is Already Active In The Memory
    if Lobby_Data["Is_Open"]: 
        Active_Error = "⚠️ Warning An Active Gaming Lobby Is Already In Operation Currently\n\n"
        Active_Error += "Multiple Lobbies Cannot Run Simultaneously In The Same Session\n"
        Active_Error += "Please Wait For The Current Match To Finish Or Use The Reset Command\n"
        Active_Error += "Current Host Is Still Managing The Existing Players Inside The Room"
        return await update.message.reply_text(Active_Error)

    # Initialize The Lobby Data With Creator Information
    user = update.message.from_user
    Lobby_Data.update({
        "Is_Open": True, 
        "Creator_Id": user.id, 
        "Players": [user.id], 
        "Player_Names": {user.id: user.first_name}
    })
    
    # Large Descriptive Invitation Message
    Invite = "🎊 A New Professional Taboo Gaming Lobby Has Been Successfully Created 🎊\n\n"
    Invite += "👤 Host Name " + user.first_name + "\n"
    Invite += "📊 Current Status Waiting For Competitive Players To Join The Session\n\n"
    
    Invite += "📝 Instructions For All Aspiring Joining Participants Below\n\n"
    Invite += "👉 Type /Join To Enter Into This Gaming Room Right Now\n"
    Invite += "👉 Type /Start Once All Of Your Friends And Participants Are Present\n"
    Invite += "👉 Note A Minimum Of Two Players Is Required For Match Activation\n\n"
    
    Invite += "🔥 Get Ready For An Intense Battle Of Words And Quick Thinking\n"
    Invite += "🌟 Only The Smartest Players Will Reach The Top Of The Leaderboard\n"
    Invite += "📢 Share This Group Link With Your Friends To Fill The Slots Quickly"
    
    await update.message.reply_text(Invite)

async def Join_Handler(update: Update, context):
    user = update.message.from_user
    
    # Check If Lobby Is Actually Open
    if not Lobby_Data["Is_Open"]: 
        No_Lobby = "❌ Error No Active Gaming Lobby Found To Join At This Moment\n\n"
        No_Lobby += "Please Ask An Administrator Or A Friend To Create A New Lobby\n"
        No_Lobby += "You Can Use The Lobby Command To Host Your Own Session Right Now\n"
        No_Lobby += "Make Sure You Are In The Correct Group To Participate In The Match"
        return await update.message.reply_text(No_Lobby)

    # Check If Player Is Already Inside The Lobby
    if user.id in Lobby_Data["Players"]: 
        Already_In = "ℹ️ Information You Are Already A Registered Member Of This Active Lobby\n\n"
        Already_In += "Please Wait Patiently For The Host To Start The Official Match\n"
        Already_In += "You Cannot Join The Same Gaming Session Multiple Times In A Row\n"
        Already_In += "Check The Current Player List To Confirm Your Successful Entry Status"
        return await update.message.reply_text(Already_In)

    # Security Check To Verify If User Has Started The Bot In Private DM
    try:
        # We Try To Send A Tiny Ghost Message Or Just Use A Dummy Call
        await context.bot.send_chat_action(chat_id=user.id, action="typing")
    except Exception:
        # If Failed It Means The User Has Not Started The Bot In DM
        Dm_Needed = "⚠️ Action Required You Must Start The Bot In Private DM First ⚠️\n\n"
        Dm_Needed += "Dear Participant " + user.first_name + " Our System Cannot Send You Secret Words\n"
        Dm_Needed += "Please Click On The Bot Username And Press The Start Button Privately\n"
        Dm_Needed += "Once You Have Started The Bot In DM Come Back Here And Type Join Again\n"
        Dm_Needed += "This Security Step Is Mandatory To Receive Your Hidden Taboo Words Later"
        return await update.message.reply_text(Dm_Needed)

    # If All Checks Pass Add The User To The Lobby
    Lobby_Data["Players"].append(user.id)
    Lobby_Data["Player_Names"][user.id] = user.first_name
    
    Success_Msg = "✅ " + user.first_name + " Has Successfully Joined The Competitive Game Lobby\n\n"
    Success_Msg += "📊 Current Total Participant Count Is Now " + str(len(Lobby_Data["Players"])) + " Active Players\n"
    Success_Msg += "🕒 We Are Still Waiting For More Friends To Join This Exciting Fun Session\n\n"
    Success_Msg += "📢 Invite Your Group Members By Sharing The Group Link Immediately\n"
    Success_Msg += "🚀 The Match Will Be Ready To Launch Once All Slots Are Fully Occupied\n"
    Success_Msg += "💎 Prepare Your Mind For The Most Challenging Taboo Experience Today"
    
    await update.message.reply_text(Success_Msg)

async def Start_Handler(update: Update, context):
    # Check If The Match Is Already Running Or Lobby Is Not Created
    if not Lobby_Data["Is_Open"]:
        return await update.message.reply_text("❌ Error There Is No Active Lobby Available To Start At This Moment")

    # Only The Person Who Created The Lobby Can Start The Match
    if update.message.from_user.id != Lobby_Data["Creator_Id"]:
        No_Permission = "🚫 Permission Denied Access To Start The Match Is Restricted Only To The Host\n\n"
        No_Permission += "Please Ask The Lobby Creator " + Lobby_Data["Player_Names"][Lobby_Data["Creator_Id"]] + " To Launch The Game\n"
        No_Permission += "Only The Official Creator Of This Session Can Initialize The Team Formation Process\n"
        No_Permission += "This Rule Ensures That All Participants Are Ready Before The Battle Begins Today"
        return await update.message.reply_text(No_Permission)

    # Verification For Minimum Players
    Total_Players = len(Lobby_Data["Players"])
    if Total_Players < 2:
        return await update.message.reply_text("⚠️ Insufficient Participants A Minimum Of Two Players Is Required To Form Teams")

    # Team Balancing Logic To Ensure Equal Players In Both Teams
    if Total_Players % 2 != 0:
        Balancing_Error = "⚖️ Team Balancing Warning The Number Of Players Must Be Even For A Fair Match\n\n"
        Balancing_Error += "Current Total Player Count Is " + str(Total_Players) + " Which Leads To Unequal Team Distribution\n"
        Balancing_Error += "Please Ask One More Friend To Use The Join Command To Balance The Competition\n"
        Balancing_Error += "We Believe In Fair Play And Equal Opportunity For Both Team A And Team B Members\n"
        Balancing_Error += "Once An Even Number Of Participants Is Reached You Can Proceed To Start The Game"
        return await update.message.reply_text(Balancing_Error)

    # Shuffle And Divide Teams Equal Distribution
    random.shuffle(Lobby_Data["Players"])
    mid = Total_Players // 2
    Game_State.update({
        "Is_Running": True, 
        "Team_A": Lobby_Data["Players"][:mid], 
        "Team_B": Lobby_Data["Players"][mid:], 
        "Scores": {"A": 0, "B": 0},
        "Current_Turn_Team": "A"
    })
    Lobby_Data["Is_Open"] = False
    
    # Grand Announcement Of Team Formation
    Battle_Msg = "⚔️ The Grand Taboo Battle Has Officially Commenced And Teams Are Now Locked ⚔️\n\n"
    
    Battle_Msg += "🟦 Roster Members Of Team Alpha\n"
    for p_id in Game_State["Team_A"]: 
        Battle_Msg += "✨ " + Lobby_Data["Player_Names"][p_id] + "\n"
    
    Battle_Msg += "\n🟥 Roster Members Of Team Bravo\n"
    for p_id in Game_State["Team_B"]: 
        Battle_Msg += "✨ " + Lobby_Data["Player_Names"][p_id] + "\n"
    
    Battle_Msg += "\n📝 Match Instructions For Both Competitive Teams Below\n\n"
    Battle_Msg += "👉 We Are Starting The First Round With Team Alpha Members Now\n"
    Battle_Msg += "👉 Please Type The Next Command To Generate Your First Secret Word Inbox\n"
    Battle_Msg += "👉 Clue Givers Must Check Their Private DM Before Giving Any Hints Today\n\n"
    
    Battle_Msg += "🔥 May The Smartest And Quickest Team Claim The Final Victory Trophy 🔥"
    
    await update.message.reply_text(Battle_Msg)

async def Next_Round_Handler(update: Update, context):
    if not Game_State["Is_Running"]: 
        Invalid_Match = "🚫 Operation Denied There Is No Active Match Currently Running In This Session\n\n"
        Invalid_Match += "Please Ensure That You Have Created A Lobby And Started The Game Properly\n"
        Invalid_Match += "Use The Lobby Command To Host A New Room And Invite Your Competitive Friends\n"
        Invalid_Match += "Once The Teams Are Formed You Can Use This Command To Begin The Rounds"
        return await update.message.reply_text(Invalid_Match)

    if Game_State["Round_Active"]:
        Busy_Error = "⚠️ Warning An Active Round Is Already Progressing In This Group Right Now\n\n"
        Busy_Error += "You Cannot Fetch A New Word Until The Current Timer Expires Or Someone Guesses Right\n"
        Busy_Error += "Please Focus On The Current Secret Word And Provide Accurate Clues To Your Team\n"
        Busy_Error += "Wait For The Current Clue Giver To Finish Their Turn Before Requesting The Next One"
        return await update.message.reply_text(Busy_Error)

    Team_Key = "Team_" + Game_State["Current_Turn_Team"]
    Current_Team_Roster = Game_State[Team_Key]
    Game_State["Clue_Giver"] = random.choice(Current_Team_Roster)
    
    Word_Obj = random.choice(Word_Library)
    
    # Fixed Lower Case Methods Here
    Game_State.update({
        "Current_Word": Word_Obj["Word"],
        "Taboo_Words": [W.lower() for W in Word_Obj["Taboo"]],
        "Round_Active": True
    })

    try:
        Dm_Msg = "🤫 Your Exclusive Secret Taboo Word Details Have Arrived Safely 🤫\n\n"
        Dm_Msg += "🎯 Your Primary Secret Word To Clue Is " + Word_Obj['Word'].upper() + "\n\n"
        Dm_Msg += "🚫 Strictly Restricted Taboo Words Mentioning These Will End Your Turn\n"
        for W in Word_Obj['Taboo']: Dm_Msg += "✨ " + W + "\n"
        Dm_Msg += "\n📝 Instructions Use The Clue Command In This Private DM To Send Hints To Group\n"
        Dm_Msg += "🚀 Example Type Clue It Is A Very Delicious Indian Fried Snack\n"
        Dm_Msg += "🔥 Good Luck Champion Try To Make Your Team Guess As Fast As Possible"
        
        await context.bot.send_message(chat_id=Game_State["Clue_Giver"], text=Dm_Msg)
        
        Announce = "🔔 A Fresh Exciting Round Has Officially Commenced For Everyone 🔔\n\n"
        Announce += "👤 Nominated Clue Giver For This Round " + Lobby_Data["Player_Names"][Game_State["Clue_Giver"]] + "\n"
        Announce += "🚩 Currently Playing Active Team Team " + Game_State["Current_Turn_Team"] + "\n\n"
        Announce += "📥 The Secret Information Has Been Delivered To The Clue Giver Private Inbox\n"
        Announce += "⏳ The Professional Game Timer Of One Hundred Twenty Seconds Is Now Active\n"
        Announce += "📢 All Team Members Should Prepare To Type Their Guesses Inside This Group\n"
        Announce += "🌟 Use Your Maximum Intelligence To Win Ten Points For Your Respective Team"
        await update.message.reply_text(Announce)
        
        asyncio.create_task(Manage_Round_Timer(update.effective_chat.id, context, Word_Obj["Word"]))
        
    except Exception:
        Fail_Msg = "❌ Critical Communication Error Could Not Deliver The Secret Message ❌\n\n"
        Fail_Msg += "It Seems The Nominated Clue Giver " + Lobby_Data["Player_Names"][Game_State["Clue_Giver"]] + " Has Blocked The Bot\n"
        Fail_Msg += "Please Ensure That You Have Started The Bot In Private DM To Receive Words\n"
        Fail_Msg += "We Are Forcing This Round To Reset So Please Use The Next Command Again"
        Game_State["Round_Active"] = False
        await update.message.reply_text(Fail_Msg)

# 1. New Handler For Receiving Clues In Private DM
async def Clue_Submit_Handler(update: Update, context):
    # Ensure This Command Is Only Used Inside Private Chat
    if update.effective_chat.type != 'private':
        return # Silent Return To Prevent Group Spam

    User = update.message.from_user
    
    # Check If The Round Is Active And User Is The Assigned Clue Giver
    if not Game_State["Round_Active"] or User.id != Game_State["Clue_Giver"]:
        Error_Dm = "🚫 Access Denied You Are Not Authorized To Submit Clues At This Moment\n\n"
        Error_Dm += "Please Wait For Your Official Turn To Become The Designated Clue Giver\n"
        Error_Dm += "Only The Player Who Received The Secret Word Can Use This Command\n"
        Error_Dm += "Current Match Status And Turn Information Is Available In The Group Chat"
        return await update.message.reply_text(Error_Dm)

    # Validate If Clue Content Is Provided
    Clue_Text = " ".join(context.args)
    if not Clue_Text:
        Usage_Dm = "📝 Instruction Please Provide Your Clue Text After The Command\n\n"
        Usage_Dm += "Example Usage Format Type Clue It Is Found Inside A Deep Jungle\n"
        Usage_Dm += "Your Clue Will Be Automatically Forwarded To The Group For Everyone\n"
        Usage_Dm += "Ensure Your Description Is Accurate Without Using Any Forbidden Words"
        return await update.message.reply_text(Usage_Dm)

    # Check For Forbidden Taboo Words Inside The Submitted Clue
    for Forbidden in Game_State["Taboo_Words"]:
        if Forbidden in Clue_Text.lower():
            Violation_Dm = "⚠️ Taboo Violation Detected Your Clue Contains A Restricted Word\n\n"
            Violation_Dm += "Forbidden Word Found " + Forbidden.upper() + "\n"
            Violation_Dm += "Please Rewrite Your Description Carefully Without Using Any Taboo Terms\n"
            Violation_Dm += "Repeated Violations Might Lead To Automatic Turn Cancellation So Be Careful"
            return await update.message.reply_text(Violation_Dm)

    # Forward The Clue To The Main Group Chat
    Group_Id = context.bot_data.get("Current_Group_Id")
    if Group_Id:
        Forward_Msg = "📣 Attention Members An Official Hint Has Been Received From The Clue Giver 📣\n\n"
        Forward_Msg += "💡 Message Description " + Clue_Text.upper() + "\n\n"
        Forward_Msg += "🔎 All Active Team Members Should Analyze This Hint And Type Their Guesses\n"
        Forward_Msg += "🕒 The Clock Is Ticking Fast So Provide Your Best Possible Answers Now\n"
        Forward_Msg += "🏆 First Correct Guess Will Win Ten Points For Your Respective Team"
        await context.bot.send_message(chat_id=Group_Id, text=Forward_Msg)
        await update.message.reply_text("✅ Success Your Clue Has Been Successfully Delivered To The Group Chat")

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
                Old_Team = Game_State["Current_Turn_Team"]
                Game_State["Current_Turn_Team"] = "B" if Old_Team == "A" else "A"
                
                Penalty_Msg = "🚫 Major Penalty Detected The Clue Giver Spoke A Taboo Word In Public 🚫\n\n"
                Penalty_Msg += "Violator Name " + User.first_name + "\n"
                Penalty_Msg += "Restricted Word Used " + Forbidden.upper() + "\n\n"
                Penalty_Msg += "This Round Is Now Terminated And The Turn Has Been Switched Immediately\n"
                Penalty_Msg += "Please Type The Next Command To Start A New Round For The Opposing Team\n"
                Penalty_Msg += "Follow The Rules To Maintain Fair Competition Within Your Gaming Session"
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
            
            Victory_Msg = "🎊 Fantastic Achievement The Secret Word Has Been Successfully Guessed 🎊\n\n"
            Victory_Msg += "👑 Winning Participant Name " + User.first_name + "\n"
            Victory_Msg += "🎯 Correct Answer Revealed " + Game_State["Current_Word"].upper() + "\n"
            Victory_Msg += "📈 Total Ten Bonus Points Have Been Awarded To Team " + Winning_Team + "\n\n"
            Victory_Msg += "You Are Showing Great Teamwork And Incredible Thinking Skills Today\n"
            Victory_Msg += "Please Type The Next Command To Proceed To The Following Exciting Round\n"
            Victory_Msg += "Keep Up The Momentum To Secure Your Spot On The Leaderboard"
            
            Game_State["Current_Word"] = None
            await update.message.reply_text(Victory_Msg)

async def Profile_Handler(update: Update, context):
    # Fetch Player Statistics From The Central Database
    Cursor.execute("Select Points, Wins, Games_Played From Players Where User_Id = ?", (update.message.from_user.id,))
    Data = Cursor.fetchone()
    
    # Check If The Player Has Any Recorded History
    if not Data: 
        No_Record = "🔍 Discovery Error No Statistics Found For This Profile In Our Central Database\n\n"
        No_Record += "It Seems You Have Not Participated In Any Official Taboo Matches Yet\n"
        No_Record += "Please Join An Active Lobby And Complete A Match To Generate Your Gaming Record\n"
        No_Record += "Your Career Progress Will Be Automatically Tracked Once You Start Scoring Points\n"
        No_Record += "We Are Looking Forward To Seeing Your Name On Our Competitive Leaderboard Soon"
        return await update.message.reply_text(No_Record)
    
    # Extract Values For Calculation
    Points = Data[0]
    Wins = Data[1]
    Total_Games = Data[2]
    
    # Calculate Win Rate Percentage For Professional Look
    Win_Rate = (Wins / Total_Games) * 100 if Total_Games > 0 else 0
    
    # Determine Player Tier Based On Career Points
    Player_Tier = "Beginner Associate"
    if Points > 500: Player_Tier = "Elite Strategist"
    if Points > 1500: Player_Tier = "Master Wordsmith"
    if Points > 5000: Player_Tier = "Grand Taboo Champion"

    # Constructing The Highly Detailed Profile Report
    Profile_Msg = "🛡️ Official Participant Gaming Profile Statistics Detailed Report 🛡️\n\n"
    
    Profile_Msg += "👤 Participant Identity Name " + update.message.from_user.first_name + "\n"
    Profile_Msg += "🎖️ Current Professional Tier " + Player_Tier + "\n\n"
    
    Profile_Msg += "📊 Detailed Performance Analytics Below\n\n"
    
    Profile_Msg += "💎 Total Career Points Accumulated " + str(Points) + " Points\n"
    Profile_Msg += "🏆 Total Official Match Victories Recorded " + str(Wins) + " Wins\n"
    Profile_Msg += "🎮 Total Competitive Games Played " + str(Total_Games) + " Matches\n"
    Profile_Msg += "📈 Overall Match Winning Probability " + str(round(Win_Rate, 2)) + " Percent\n\n"
    
    Profile_Msg += "📝 Management Notes And Career Advice\n"
    Profile_Msg += "You Are Currently Ranked Within The " + Player_Tier + " Category Based On Your Skills\n"
    Profile_Msg += "Continue Participating In More Rounds To Improve Your Overall Winning Percentage\n"
    Profile_Msg += "Winning Consecutive Rounds Will Help You Reach The Grand Taboo Champion Status Faster\n\n"
    
    Profile_Msg += "🌟 Keep Playing Regularly To Secure Your Legacy In Our Global Hall Of Fame 🌟"
    
    await update.message.reply_text(Profile_Msg)

async def Leaderboard_Handler(update: Update, context):
    # Fetch Top Ten Players Instead Of Just Five For A More Competitive Board
    Cursor.execute("Select Name, Points From Players Order By Points Desc Limit 10")
    Ranks = Cursor.fetchall()
    
    # Check If The Leaderboard Database Has Any Entries
    if not Ranks:
        Empty_Board = "📭 Database Alert The Global Leaderboard Is Currently Empty\n\n"
        Empty_Board += "It Seems No Players Have Scored Any Points In The Current Season Yet\n"
        Empty_Board += "Be The First Participant To Win A Match And Claim The Top Position Here\n"
        Empty_Board += "Start A New Game Lobby Now To Begin Your Journey Towards Becoming A Legend"
        return await update.message.reply_text(Empty_Board)
    
    # Constructing The Professional Hall Of Fame Board
    Board = "🏆 Presenting The Official Taboo Global Hall Of Fame Top Rankings 🏆\n\n"
    Board += "Witness The Greatest Minds And Quickest Thinkers In Our Community Today\n\n"
    
    for Index, Player in enumerate(Ranks):
        Position = Index + 1
        Player_Name = Player[0]
        Player_Points = Player[1]
        
        # Assigning Professional Medals For Top Three Positions
        if Position == 1:
            Rank_Icon = "🥇 First Place"
        elif Position == 2:
            Rank_Icon = "🥈 Second Place"
        elif Position == 3:
            Rank_Icon = "🥉 Third Place"
        else:
            Rank_Icon = "🏅 Position " + str(Position)
            
        Board += Rank_Icon + " Participant Name " + Player_Name + " With Total Career Points " + str(Player_Points) + "\n"
    
    Board += "\n📊 Global Ranking Summary And Competition Status\n"
    Board += "The Battle For The Top Position Is Getting Extremely Intense This Season\n"
    Board += "Do You Have The Intelligence And Speed To Surpass These Legendary Players\n"
    Board += "Every Correct Guess Brings You Closer To The Prestigious Gold Medal Status\n\n"
    
    Board += "✨ Keep Playing Regularly To Secure Your Legacy On This Famous Board ✨"
    
    await update.message.reply_text(Board)

# Function To Show Current Lobby Members
async def Members_Handler(update: Update, context):
    if not Lobby_Data["Players"]:
        return await update.message.reply_text("🔍 System Alert The Lobby Is Currently Empty With No Active Participants")
    
    Member_List = "👥 Current Professional Gaming Lobby Participant Roster 👥\n\n"
    for P_Id in Lobby_Data["Players"]:
        Member_List += "✨ Participant Name " + Lobby_Data["Player_Names"][P_Id] + "\n"
    
    Member_List += "\n📊 Total Count Of Players Currently Waiting In This Session " + str(len(Lobby_Data["Players"]))
    await update.message.reply_text(Member_List)

# Function To Show Team Distribution
async def Team_Handler(update: Update, context):
    if not Game_State["Is_Running"]:
        return await update.message.reply_text("🚫 Error Teams Are Not Formed Until The Official Match Begins")
    
    Team_Msg = "⚔️ Official Team Distribution Roster For The Current Match ⚔️\n\n"
    Team_Msg += "🟦 Roster Members Of Team Alpha\n"
    for P_Id in Game_State["Team_A"]: Team_Msg += "✨ " + Lobby_Data["Player_Names"][P_Id] + "\n"
    
    Team_Msg += "\n🟥 Roster Members Of Team Bravo\n"
    for P_Id in Game_State["Team_B"]: Team_Msg += "✨ " + Lobby_Data["Player_Names"][P_Id] + "\n"
    
    await update.message.reply_text(Team_Msg)

# Function To Provide A Visual Hint To The Group
async def Hint_Handler(update: Update, context):
    if not Game_State["Round_Active"]:
        return await update.message.reply_text("🚫 System Alert There Is No Active Secret Word To Provide A Hint For")
    
    Secret = Game_State["Current_Word"]
    # Generates A Masked Hint Like A _ _ L E
    Masked = Secret[0] + " " + " ".join(["_" for _ in range(len(Secret)-1)])
    
    Hint_Msg = "💡 Official System Hint Generated For The Current Secret Word 💡\n\n"
    Hint_Msg += "🔎 Word Structure Format " + Masked.upper() + "\n"
    Hint_Msg += "📏 Total Number Of Characters In The Hidden Word " + str(len(Secret)) + "\n\n"
    Hint_Msg += "📢 Everyone Please Use This Structural Information To Refine Your Guesses"
    await update.message.reply_text(Hint_Msg)

# Function To Check Whose Turn It Is
async def Turn_Handler(update: Update, context):
    if not Game_State["Is_Running"]:
        return await update.message.reply_text("🔍 Match Status No Active Turn Recording Since The Game Has Not Started")
    
    Team_Name = "Team Alpha" if Game_State["Current_Turn_Team"] == "A" else "Team Bravo"
    Turn_Report = "🔄 Official Turn Assignment Tracking Report 🔄\n\n"
    Turn_Report += "🚩 Current Active Turn Belongs To " + Team_Name + "\n"
    
    if Game_State["Round_Active"]:
        Turn_Report += "👤 Current Assigned Clue Giver " + Lobby_Data["Player_Names"][Game_State["Clue_Giver"]] + "\n"
        Turn_Report += "🕒 Remaining Time Is Ticking Down In The Background Task\n"
    else:
        Turn_Report += "🕒 Status Waiting For The Authorized Member To Type The Next Command\n"
    
    await update.message.reply_text(Turn_Report)

async def Reset_Handler(update: Update, context):
    # Accessing Global Variables To Perform A Complete System Wipe
    global Lobby_Data, Game_State
    
    # Fully Resetting The Lobby Information To Factory Default
    Lobby_Data.update({
        "Is_Open": False, 
        "Creator_Id": None, 
        "Players": [], 
        "Player_Names": {}
    })
    
    # Fully Resetting The Game State Information To Default Values
    Game_State.update({
        "Is_Running": False, 
        "Team_A": [], 
        "Team_B": [], 
        "Scores": {"A": 0, "B": 0},
        "Current_Turn_Team": "A", 
        "Current_Word": None, 
        "Taboo_Words": [], 
        "Clue_Giver": None, 
        "Round_Active": False
    })
    
    # Constructing The Professional System Reset Announcement
    Reset_Msg = "🔄 The Professional Taboo Game Engine Has Been Successfully Reset 🔄\n\n"
    
    Reset_Msg += "🧹 All Current Session Data And Match Records Have Been Wiped Clean\n"
    Reset_Msg += "🛡️ The System Memory Is Now Initialized To Factory Default Settings\n"
    Reset_Msg += "👤 Any Active Lobby Or Round Progress Has Been Permanently Terminated\n\n"
    
    Reset_Msg += "📝 Important Instructions For Starting A New Gaming Session\n"
    Reset_Msg += "You Are Now Authorized To Create A Brand New Lobby Using The Lobby Command\n"
    Reset_Msg += "Ensure All Players Are Ready To Rejoin Before You Initialize The Teams Again\n"
    Reset_Msg += "The Scores Of The Previous Session Are Not Saved In Temporary Memory\n\n"
    
    Reset_Msg += "🌟 Thank You For Using Our Automated Gaming Management System 🌟"
    
    await update.message.reply_text(Reset_Msg)

async def Status_Handler(update: Update, context):
    # Verification Check If The Game Is Actually Active
    if not Game_State["Is_Running"]: 
        No_Game = "🔍 Information No Active Taboo Game Match Is Currently In Progress\n\n"
        No_Game += "There Are No Scores To Display Because The Game Engine Is Idle\n"
        No_Game += "Please Use The Lobby Command To Create A New Session First\n"
        No_Game += "Once The Match Starts You Can Use Status To Track Your Progress"
        return await update.message.reply_text(No_Game)
    
    # Constructing The Grand Status Report Header
    Status_Report = "📊 Presenting The Current Detailed Match Status Professional Report 📊\n\n"
    
    # Score Display Section
    Score_A = Game_State["Scores"]["A"]
    Score_B = Game_State["Scores"]["B"]
    
    Status_Report += "🟦 Team Alpha Current Performance Score " + str(Score_A) + " Points\n"
    Status_Report += "🟥 Team Bravo Current Performance Score " + str(Score_B) + " Points\n\n"
    
    # Advanced Leadership Analysis Logic
    Status_Report += "🏆 Current Match Leadership Status Analysis\n"
    if Score_A > Score_B:
        Difference = Score_A - Score_B
        Status_Report += "Dominating Team Team Alpha Is Leading By " + str(Difference) + " Points\n"
    elif Score_B > Score_A:
        Difference = Score_B - Score_A
        Status_Report += "Dominating Team Team Bravo Is Leading By " + str(Difference) + " Points\n"
    else:
        Status_Report += "Competitive Status Both Teams Are Currently Standing On Equal Scores\n"
        
    # Current Turn And Round Dynamics
    Status_Report += "\n🎮 Current Active Turn Details\n"
    Current_Team_Name = "Team Alpha" if Game_State["Current_Turn_Team"] == "A" else "Team Bravo"
    Status_Report += "Currently Playing Right Now " + Current_Team_Name + "\n"
    
    if Game_State["Round_Active"]:
        Clue_Giver_Name = Lobby_Data["Player_Names"].get(Game_State["Clue_Giver"], "Unknown Participant")
        Status_Report += "Round Status Active Word Guessing Is Currently Ongoing\n"
        Status_Report += "Designated Clue Giver " + Clue_Giver_Name + "\n"
        Status_Report += "Timer Status The Clock Is Ticking Towards The Final Seconds\n"
    else:
        Status_Report += "Round Status Waiting For The Next Secret Word Initialization\n"
        Status_Report += "Instruction Please Type The Next Command To Start The Following Round\n"
    
    Status_Report += "\n✨ Keep Playing And Perform Better To Secure Your Ultimate Victory ✨"
    
    await update.message.reply_text(Status_Report)

async def Guide_Handler(update: Update, context):
    Guide_Text = "📖 Professional Taboo Gaming Guide For Beginners And New Players 📖\n\n"
    
    Guide_Text += "Agar Aap Is Game Mein Naye Hain Toh Yeh Guide Aapko Master Bana Degi\n\n"
    
    Guide_Text += "📍 Step 1 Game Kaise Join Karein\n"
    Guide_Text += "Sabse Pehle Bot Ke Username Par Click Karke Use Private Mein Start Button Dabayein\n"
    Guide_Text += "Uske Baad Group Mein Aakar Join Likhein Taaki Aap Match Ka Hissa Ban Sakein\n"
    Guide_Text += "Jab Tak Teams Barabar Nahi Hongi Tab Tak Game Shuru Nahi Hoga Isliye Doston Ko Bulayein\n\n"
    
    Guide_Text += "📍 Step 2 Clue Giver Ka Kaam Kya Hai\n"
    Guide_Text += "Har Round Mein Ek Player Ko Word Batane Wala Matlab Clue Giver Banaya Jayega\n"
    Guide_Text += "Bot Aapko Private Message Mein Ek Secret Word Aur Panch Mana Kiye Gaye Words Bhejega\n"
    Guide_Text += "Aapko Woh Secret Word Apni Team Ko Samjhana Hai Lekin Woh Panch Words Use Nahi Karne Hain\n"
    Guide_Text += "Hint Dene Ke Liye Bot Ke DM Mein Clue Aur Apna Message Likhein Jaise Clue Yeh Peela Phal Hai\n\n"
    
    Guide_Text += "📍 Step 3 Guess Kaise Karna Hai\n"
    Guide_Text += "Baaki Saare Players Ko Group Chat Mein Sirf Woh Word Type Karna Hai Jo Unhe Lagta Hai Sahi Hai\n"
    Guide_Text += "Aapko Koi Command Use Nahi Karni Hai Bas Direct Word Likhein Jaise Mango Ya Apple\n"
    Guide_Text += "Jo Sabse Pehle Sahi Word Likhega Uski Team Ko Das Points Mil Jayenge\n\n"
    
    Guide_Text += "📍 Step 4 Galatiyon Se Kaise Bachein\n"
    Guide_Text += "Clue Giver Ko Kabhi Bhi Group Chat Mein Hint Nahi Likhna Hai Hamesha Bot Ke DM Mein Likhein\n"
    Guide_Text += "Agar Clue Giver Ne Mana Kiye Gaye Words Bole Toh Round Turant Khatam Ho Jayega\n"
    Guide_Text += "Hamesha Timer Par Nazar Rakhein Kyunki Do Minute Baad Round Apne Aap Band Ho Jayega\n\n"
    
    Guide_Text += "📍 Example Uddahran Ke Liye\n"
    Guide_Text += "Secret Word Samosa Hai Aur Taboo Word Aloo Hai\n"
    Guide_Text += "Aap DM Mein Likhenge Clue Yeh Ek Tikona Nashta Hai Jo Fry Hota Hai\n"
    Guide_Text += "Aap Aloo Word Use Nahi Kar Sakte Warna Penalty Lag Jayegi\n\n"
    
    Guide_Text += "🌟 Bas Itna Hi Hai Ab Khelna Shuru Karein Aur Points Jeetein 🌟"
    
    await update.message.reply_text(Guide_Text)

async def Rules_Handler(update: Update, context):
    Summary = "🎮 Welcome To The Ultimate Professional Taboo Game Comprehensive Guide 🎮\n\n"
    
    Summary += "This Game Is A Thrilling Battle Of Words Intelligence And Quick Thinking Between Two Competitive Teams\n\n"
    
    Summary += "📍 Phase One Creating The Lobby And Forming Teams\n"
    Summary += "First One Player Must Create A Lobby Using The Lobby Command Inside The Group Chat\n"
    Summary += "Other Interested Participants Must Join The Session By Using The Join Command To Register Themselves\n"
    Summary += "The Host Will Start The Match Once Teams Are Balanced Equally Into Team Alpha And Team Bravo\n\n"
    
    Summary += "📍 Phase Two The Secret Word And Clue Submission\n"
    Summary += "Every Round One Player Is Nominated As The Official Clue Giver For Their Respective Team\n"
    Summary += "The Bot Will Send A Secret Word Along With Five Restricted Taboo Words To Their Private DM\n"
    Summary += "The Clue Giver Must Describe The Secret Word Without Using Any Of Those Forbidden Taboo Words\n"
    Summary += "Important Note Clues Must Be Submitted Only In The Bot Private DM Using The Clue Command\n\n"
    
    Summary += "📍 Phase Three Guessing And Scoring Points\n"
    Summary += "Once The Clue Is Forwarded To The Group Chat All Other Members Must Start Guessing The Word\n"
    Summary += "Participants Should Type Their Guesses Directly Into The Group Chat Without Using Any Commands\n"
    Summary += "The First Person To Type The Correct Secret Word Wins Ten Points For Their Team Immediately\n"
    Summary += "If The Clue Giver Accidentally Mentions A Taboo Word The Turn Ends And No Points Are Awarded\n\n"
    
    Summary += "📍 Phase Four The Professional Timer And Victory\n"
    Summary += "Each Round Features A One Hundred Twenty Second Professional Timer With Multiple Warning Alerts\n"
    Summary += "If No One Guesses The Correct Word Within The Time Limit The Round Ends And The Turn Shifts\n"
    Summary += "Players Can Track Their Performance Records Using The Profile And Global Leaderboard Commands\n\n"
    
    Summary += "🌟 Follow These Professional Rules To Maintain Fair Competition And Become A Grand Champion 🌟"
    
    await update.message.reply_text(Summary)

async def Cancel_Handler(update: Update, context):
    # Check If There Is Actually Anything To Cancel
    if not Lobby_Data["Is_Open"] and not Game_State["Is_Running"]:
        Empty_Error = "❌ Operation Denied There Is No Active Lobby Or Match To Cancel ❌\n\n"
        Empty_Error += "The Gaming Engine Is Already In An Idle State Currently\n"
        Empty_Error += "You Can Create A New Session By Using The Lobby Command Anytime\n"
        Empty_Error += "No Resources Are Currently Being Used By The System Memory"
        return await update.message.reply_text(Empty_Error)

    # Security Check Only The Creator Or An Admin Can Cancel
    User_Id = update.message.from_user.id
    if User_Id != Lobby_Data["Creator_Id"]:
        # Optional You Can Add Admin Check Here Too
        No_Auth = "🚫 Access Restricted Only The Official Host Can Cancel This Match 🚫\n\n"
        No_Auth += "Participant Name " + update.message.from_user.first_name + " Is Not Authorized\n"
        No_Auth += "Please Request The Lobby Creator To Terminate The Session Properly\n"
        No_Auth += "This Protocol Prevents Unauthorized Termination Of Active Gaming Rounds"
        return await update.message.reply_text(No_Auth)

    # Performing The Full System Reset For Cancellation
    global Lobby_Data, Game_State
    Lobby_Data.update({"Is_Open": False, "Creator_Id": None, "Players": [], "Player_Names": {}})
    Game_State.update({
        "Is_Running": False, 
        "Round_Active": False, 
        "Current_Word": None, 
        "Team_A": [], 
        "Team_B": [], 
        "Scores": {"A": 0, "B": 0}
    })
    
    Termination_Msg = "🛑 Official Match Cancellation Notice Successfully Processed 🛑\n\n"
    Termination_Msg += "The Current Gaming Session Has Been Terminated By The Authorized Host\n"
    Termination_Msg += "All Active Rounds Scores And Team Formations Have Been Wiped Clean\n"
    Termination_Msg += "The Bot Memory Is Now Initialized Back To The Standard Default State\n\n"
    
    Termination_Msg += "📝 Management Information For All Participants Below\n"
    Termination_Msg += "You Are Now Free To Initiate A Brand New Match Session Using Lobby Command\n"
    Termination_Msg += "We Hope To See You Back In The Competitive Arena Very Soon Indeed\n\n"
    
    Termination_Msg += "🌟 Thank You For Utilizing Our Professional Taboo Management Services 🌟"
    
    await update.message.reply_text(Termination_Msg)

def main():
    Token_Val = "8380924465:AAFwbA-55qfkrA0-QJ_AL2uWuuS3Pt7y-Mw"
    Application = ApplicationBuilder().token(Token_Val).connect_timeout(40).read_timeout(40).write_timeout(40).pool_timeout(40).build()
    
    Application.add_handler(CommandHandler("help", Help_Handler))
    Application.add_handler(CommandHandler("lobby", Lobby_Handler))
    Application.add_handler(CommandHandler("join", Join_Handler))
    Application.add_handler(CommandHandler("start", Start_Handler))
    Application.add_handler(CommandHandler("round", Next_Round_Handler))
    Application.add_handler(CommandHandler("cancel", Cancel_Handler))
    Application.add_handler(CommandHandler("status", Status_Handler))
    Application.add_handler(CommandHandler("profile", Profile_Handler))
    Application.add_handler(CommandHandler("leaderboard", Leaderboard_Handler))
    Application.add_handler(CommandHandler("reset", Reset_Handler))
    Application.add_handler(CommandHandler("clue", Clue_Submit_Handler))
    Application.add_handler(CommandHandler("rule", Rules_Handler))
    Application.add_handler(CommandHandler("members", Members_Handler))
    Application.add_handler(CommandHandler("team", Team_Handler))
    Application.add_handler(CommandHandler("hint", Hint_Handler))
    Application.add_handler(CommandHandler("turn", Turn_Handler))
    Application.add_handler(CommandHandler("guide", Guide_Handler))
    Application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), Referee_Logic))
    
    print("Taboo Professional Engine Is Live ✨")
    Application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
