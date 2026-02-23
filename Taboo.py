import os
import sqlite3
import random
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackQueryHandler
)

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
    "History": []
}

def Initialize_Database():
    Conn = sqlite3.connect('Taboo_Data.db', check_same_thread=False)
    Cursor = Conn.cursor()
    Cursor.execute('''Create Table If Not Exists Players 
                    (User_Id Integer Primary Key, Name Text, Points Integer Default 0, Wins Integer Default 0)''')
    Conn.commit()
    return Conn, Cursor

Db_Conn, Db_Cursor = Initialize_Database()

def Update_Player_Stats(user_id, name, points_earned):
    Db_Cursor.execute("Select User_Id From Players Where User_Id = ?", (user_id,))
    Data = Db_Cursor.fetchone()
    
    if not Data:
        Db_Cursor.execute("Insert Into Players (User_Id, Name, Points) Values (?, ?, ?)", (user_id, name, points_earned))
    else:
        Db_Cursor.execute("Update Players Set Points = Points + ? Where User_Id = ?", (points_earned, user_id))
    Db_Conn.commit()

Category_Words = {
    "Bollywood": [
        {"Word": "Sholay", "Taboo": ["Gabbar", "Basanti", "Amitabh", "Movie", "Thakur"]},
        {"Word": "Dangal", "Taboo": ["Aamir", "Wrestling", "Geeta", "Babita", "Movie"]},
        {"Word": "Lagaan", "Taboo": ["Cricket", "Aamir", "Tax", "British", "Village"]},
        {"Word": "Tiger", "Taboo": ["Salman", "Zoya", "Spy", "Katrina", "Movie"]},
        {"Word": "Kabir Singh", "Taboo": ["Shahid", "Doctor", "Preeti", "Angry", "Arjun Reddy"]},
        {"Word": "Pushpa", "Taboo": ["Allu", "Red", "Sandalwood", "Jhukega", "Flower"]},
        {"Word": "Pathaan", "Taboo": ["Shah Rukh", "Deepika", "John", "Spy", "Besharam"]},
        {"Word": "Jawan", "Taboo": ["SRK", "Double Role", "Metre", "Azad", "Vikram"]},
        {"Word": "Animal", "Taboo": ["Ranbir", "Bobby", "Papa", "Rashmika", "Violent"]},
        {"Word": "Gadar", "Taboo": ["Sunny", "Pakistan", "Handpump", "Tara Singh", "Amisha"]},
        {"Word": "Baahubali", "Taboo": ["Prabhas", "Katappa", "Mahishmati", "Waterfall", "Sword"]},
        {"Word": "PK", "Taboo": ["Alien", "Aamir", "Radio", "Godman", "Yellow"]},
        {"Word": "Brahmastra", "Taboo": ["Ranbir", "Alia", "Shiva", "Isha", "Astras"]},
        {"Word": "3 Idiots", "Taboo": ["College", "Aamir", "Rancho", "Engineering", "Virus"]}
    ],
    "Cricket": [
        {"Word": "Kohli", "Taboo": ["King", "Anushka", "Bat", "Century", "India"]},
        {"Word": "Dhoni", "Taboo": ["Captain", "Mahi", "7", "Keeper", "Chennai"]},
        {"Word": "Sixer", "Taboo": ["Bat", "Boundary", "Ball", "Over", "Gayle"]},
        {"Word": "Umpire", "Taboo": ["Out", "Finger", "Decision", "Ground", "Review"]},
        {"Word": "IPL", "Taboo": ["T20", "League", "Money", "Teams", "BCCI"]},
        {"Word": "Rohit", "Taboo": ["Hitman", "Mumbai", "Captain", "Vadapav", "Sharma"]},
        {"Word": "Stadium", "Taboo": ["Ground", "Pitch", "Match", "Crowd", "Tickets"]},
        {"Word": "World Cup", "Taboo": ["Odi", "Trophy", "India", "Final", "Tournament"]},
        {"Word": "Free Hit", "Taboo": ["No Ball", "Swing", "Bat", "Run", "Over"]},
        {"Word": "Stumping", "Taboo": ["Dhoni", "Keeper", "Bails", "Line", "Out"]},
        {"Word": "Century", "Taboo": ["100", "Runs", "Bat", "Celebration", "Ton"]},
        {"Word": "Hardik", "Taboo": ["Pandya", "Allrounder", "Mumbai", "Gujarat", "Kung Fu"]},
        {"Word": "Bowling", "Taboo": ["Fast", "Spin", "Over", "Wicket", "Ball"]},
        {"Word": "Catch", "Taboo": ["Hands", "Out", "Fielder", "Boundary", "Drop"]}
    ],
    "General": [
        {"Word": "Samosa", "Taboo": ["Aloo", "Chutney", "Snack", "Fried", "Tea"]},
        {"Word": "Mobile", "Taboo": ["Phone", "Call", "Screen", "App", "Battery"]},
        {"Word": "School", "Taboo": ["Teacher", "Student", "Book", "Class", "Study"]},
        {"Word": "Internet", "Taboo": ["Wifi", "Google", "Data", "Online", "Website"]},
        {"Word": "Zomato", "Taboo": ["Food", "Delivery", "App", "Order", "Restaurant"]},
        {"Word": "Metro", "Taboo": ["Train", "Token", "Delhi", "Card", "Travel"]},
        {"Word": "Instagram", "Taboo": ["Reels", "Post", "Story", "Like", "Follow"]},
        {"Word": "WhatsApp", "Taboo": ["Message", "Status", "Chat", "Blue Tick", "Group"]},
        {"Word": "Youtube", "Taboo": ["Video", "Channel", "Subscribe", "Vlog", "Content"]},
        {"Word": "Chai", "Taboo": ["Tea", "Milk", "Sugar", "Biscuit", "Cup"]},
        {"Word": "Maggi", "Taboo": ["Noodles", "2 Minutes", "Masala", "Hostel", "Hungry"]},
        {"Word": "Helmet", "Taboo": ["Bike", "Safety", "Police", "Challan", "Head"]},
        {"Word": "Aeroplane", "Taboo": ["Fly", "Sky", "Pilot", "Airport", "Flight"]},
        {"Word": "Laptop", "Taboo": ["Computer", "Office", "Keyboard", "Work", "Dell"]}
    ]
}

async def Set_Category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    Buttons = [
        [InlineKeyboardButton("Bollywood 🎭", callback_data="Cat_Bollywood"),
         InlineKeyboardButton("Cricket 🏏", callback_data="Cat_Cricket")]
    ]
    await update.message.reply_text("Kripya Game Ki Category Chunein:", reply_markup=InlineKeyboardMarkup(Buttons))

def Get_Match_Mvp():
    if not Game_State["Round_Log"]:
        return "Koi Nahi"
    
    Mvp_Id = max(Game_State["Round_Log"], key=Game_State["Round_Log"].get)
    return Lobby_Data["Player_Names"].get(Mvp_Id, "Unknown")

async def Create_Lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    User = update.message.from_user
    
    if Lobby_Data["Is_Open"]:
        await update.message.reply_text(f"Ek Lobby Pehle Se Bani Hui Hai ⚠️")
        return

    Lobby_Data["Is_Open"] = True
    Lobby_Data["Creator_Id"] = User.id
    Lobby_Data["Players"].append(User.id)
    Lobby_Data["Player_Names"][User.id] = User.first_name
    
    Msg = f"🎮 Nayi Taboo Lobby Taiyaar Hai!\n\n"
    Msg += f"👑 Creator: {User.first_name}\n"
    Msg += f"📝 Join Karne Ke Liye /Join Likhein\n"
    Msg += f"❌ Cancel Karne Ke Liye /Cancel Likhein"
    
    await update.message.reply_text(Msg)

async def Join_Lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    User = update.message.from_user
    
    if not Lobby_Data["Is_Open"]:
        await update.message.reply_text("Abhi Koi Active Lobby Nahi Hai 🚫")
        return
    
    if User.id in Lobby_Data["Players"]:
        await update.message.reply_text(f"{User.first_name}, Aap Pehle Se Join Ho! ✅")
        return

    Lobby_Data["Players"].append(User.id)
    Lobby_Data["Player_Names"][User.id] = User.first_name
    
    Msg = f"👋 {User.first_name} Ne Lobby Join Kar Li Hai!\n"
    Msg += f"👥 Total Players: {len(Lobby_Data['Players'])}"
    await update.message.reply_text(Msg)

async def Leave_Lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    User = update.message.from_user
    
    if User.id not in Lobby_Data["Players"]:
        await update.message.reply_text("Aap Is Lobby Mein Nahi Ho ❌")
        return

    Lobby_Data["Players"].remove(User.id)
    del Lobby_Data["Player_Names"][User.id]
    
    if User.id == Lobby_Data["Creator_Id"]:
        if len(Lobby_Data["Players"]) > 0:
            Lobby_Data["Creator_Id"] = Lobby_Data["Players"][0]
            New_Admin = Lobby_Data["Player_Names"][Lobby_Data["Creator_Id"]]
            await update.message.reply_text(f"Creator Ne Leave Kiya. Ab {New_Admin} Naye Host Hain! 👑")
        else:
            Lobby_Data["Is_Open"] = False
            await update.message.reply_text("Sab Players Chale Gaye. Lobby Band Ho Gayi Hai 📉")
            return

    await update.message.reply_text(f"{User.first_name} Ne Lobby Chhod Di Hai 👋")

def Switch_Team_Turn():
    if Game_State["Current_Turn_Team"] == "A":
        Game_State["Current_Turn_Team"] = "B"
    else:
        Game_State["Current_Turn_Team"] = "A"

async def Show_Players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not Lobby_Data["Is_Open"]:
        await update.message.reply_text("Lobby Khali Hai 😶")
        return
    
    List_Text = "👥 Current Players In Lobby:\n\n"
    for i, P_Id in enumerate(Lobby_Data["Players"], 1):
        Name = Lobby_Data["Player_Names"][P_Id]
        Role = "👑" if P_Id == Lobby_Data["Creator_Id"] else "👤"
        List_Text += f"{i}. {Name} {Role}\n"
    
    await update.message.reply_text(List_Text)

async def Cancel_Lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    User = update.message.from_user
    
    if not Lobby_Data["Is_Open"]:
        return

    if User.id != Lobby_Data["Creator_Id"]:
        await update.message.reply_text("Sirf Game Creator Hi Lobby Cancel Kar Sakta Hai! ⛔")
        return

    Lobby_Data["Is_Open"] = False
    Lobby_Data["Players"] = []
    Lobby_Data["Player_Names"] = {}
    Lobby_Data["Creator_Id"] = None
    
    await update.message.reply_text("Game Creator Ne Lobby Cancel Kar Di Hai 🛑")

async def Handle_Category_Selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    Query = update.callback_query
    await Query.answer()
    Category = Query.data.replace("Cat_", "")
    Game_State["Category"] = Category
    await Query.edit_message_text(f"Game Ki Category Ab {Category} Set Ho Gayi Hai! ✅")

async def Start_Game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    User = update.message.from_user
    
    if not Lobby_Data["Is_Open"]:
        await update.message.reply_text("Pehle /Lobby Banayein Phir Start Karein! ⚠️")
        return
    
    if User.id != Lobby_Data["Creator_Id"]:
        await update.message.reply_text("Sirf Game Creator Hi Shuru Kar Sakta Hai! ⛔")
        return
    
    Total_Players = Lobby_Data["Players"]
    if len(Total_Players) < 2:
        await update.message.reply_text("Kam Se Kam 2 Players Ka Hona Zaroori Hai! 👥")
        return
      
    random.shuffle(Total_Players)
    Mid = len(Total_Players) // 2
    Game_State["Team_A"] = Total_Players[:Mid]
    Game_State["Team_B"] = Total_Players[Mid:]
    
    Game_State["Is_Running"] = True
    Lobby_Data["Is_Open"] = False
    
    Msg = "🎮 Game Shuru Ho Chuka Hai!\n\n"
    
    Msg += "🔴 Team A:\n"
    for P_Id in Game_State["Team_A"]:
        Msg += f"- {Lobby_Data['Player_Names'][P_Id]}\n"
        
    Msg += "\n🔵 Team B:\n"
    for P_Id in Game_State["Team_B"]:
        Msg += f"- {Lobby_Data['Player_Names'][P_Id]}\n"
        
    Msg += f"\n🎲 Pehli Baari: Team {Game_State['Current_Turn_Team']} Ki Hai!\n"
    Msg += "Taiyaar Ho Jao! Agla Word Aa Raha Hai... 🚀"
    
    await update.message.reply_text(Msg)

async def Next_Round(update: Update, context: ContextTypes.DEFAULT_TYPE):
    Current_Team_Key = f"Team_{Game_State['Current_Turn_Team']}"
    Current_Players = Game_State[Current_Team_Key]

    if not Current_Players:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Teams Mein Players Nahi Hain! ⚠️")
        return
      
    Game_State["Clue_Giver"] = random.choice(Current_Players)
    Clue_Giver_Name = Lobby_Data["Player_Names"][Game_State["Clue_Giver"]]
    
    Selected_Data = random.choice(Category_Words)
    Game_State["Current_Word"] = Selected_Data["Word"]
    Game_State["Taboo_Words"] = [W.lower() for W in Selected_Data["Taboo"]]
    
    try:
        Secret_Msg = f"🤫 Aapka Secret Word Hai: {Game_State['Current_Word']}\n\n"
        Secret_Msg += "🚫 Ye Taboo Words Use Mat Karna:\n"
        for Word in Selected_Data["Taboo"]:
            Secret_Msg += f"- {Word}\n"
        
        await context.bot.send_message(chat_id=Game_State["Clue_Giver"], text=Secret_Msg)
        
        Group_Msg = f"📢 Agla Round Shuru!\n\n"
        Group_Msg += f"👤 Clue Giver: {Clue_Giver_Name}\n"
        Group_Msg += f"👥 Team: {Game_State['Current_Turn_Team']}\n\n"
        Group_Msg += "Baki Sab Guess Karien! Clue Giver Bolna Shuru Karein 🎙️"
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=Group_Msg)
        
    except Exception:
        Error_Msg = f"❌ {Clue_Giver_Name} Ko Word Nahi Bhej Saka! Kya Unhone Bot Ko Private Mein /Start Kiya Hai?"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=Error_Msg)
        
        asyncio.create_task(Round_Timer(update.effective_chat.id, context, Game_State["Current_Word"]))

async def Message_Referee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not Game_State["Is_Running"]:
        return

    User = update.message.from_user
    Text_Received = update.message.text.lower().strip()
    Current_Chat_Id = update.effective_chat.id
    
    if User.id == Game_State["Clue_Giver"]:
        for Forbidden in Game_State["Taboo_Words"]:
            if Forbidden in Text_Received:
                Game_State["Is_Running"] = False
                Msg = f"Galti Kar Di! {User.first_name} Ne Taboo Word '{Forbidden}' Bol Diya ⛔\n\n"
                Msg += f"Is Round Mein Team {Game_State['Current_Turn_Team']} Ko Koi Point Nahi Milega.\n"
                Msg += f"Sahi Word Tha: {Game_State['Current_Word']}\n\n"
                Msg += "Turn Switch Ho Rahi Hai... Agla Round Shuru Karne Ke Liye /Next Likhein 🔄"
                
                Switch_Team_Turn()
                await update.message.reply_text(Msg)
                return
              
    else:
        if Text_Received == Game_State["Current_Word"].lower():
            Team_Key = Game_State["Current_Turn_Team"]
            Game_State["Scores"][Team_Key] += 1
            
            Update_Player_Stats(User.id, User.first_name, points_to_add=10)
            
            Msg = f"Wah! {User.first_name} Ne Sahi Pehchana! 🎉\n\n"
            Msg += f"Sahi Jawab Tha: {Game_State['Current_Word']}\n"
            Msg += f"Team {Team_Key} Ko 10 Points Milte Hain 🏆\n\n"
            Msg += f"Agla Round Shuru Karne Ke Liye /Next Likhein 🚀"
            
            Game_State["Is_Running"] = False
            Switch_Team_Turn()
            await update.message.reply_text(Msg)

async def Round_Timer(chat_id, context: ContextTypes.DEFAULT_TYPE, round_word):
    await asyncio.sleep(120)
    
    if Game_State["Is_Running"] and Game_State["Current_Word"] == round_word:
        Game_State["Is_Running"] = False
        
        Msg = "Waqt Khatam! ⏰\n\n"
        Msg += f"Koi Bhi Sahi Jawab Nahi De Paya. Sahi Word Tha: {Game_State['Current_Word']}\n"
        Msg += "Ab Agli Team Ki Baari Hai. /Next Se Shuru Karein 🔄"
        
        Switch_Team_Turn()
        await context.bot.send_message(chat_id=chat_id, text=Msg)

async def Show_Leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    Cursor.execute("Select Name, Points From Players Order By Points Desc Limit 5")
    Top_Players = Cursor.fetchall()
    
    if not Top_Players:
        await update.message.reply_text("Abhi Tak Kisi Ka Record Nahi Hai! 😶")
        return

    Msg = "🏆 Taboo Legends Leaderboard 🏆\n\n"
    for i, (Name, Points) in enumerate(Top_Players, 1):
        Msg += f"{i}. {Name} - {Points} Points 🎖️\n"
    
    Msg += "\nKya Aap Is List Mein Aa Sakte Hain? Khelte Rahiye! 🚀"
    await update.message.reply_text(Msg)

async def My_Profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    User = update.message.from_user
    Cursor.execute("Select Points, Wins, Games_Played From Players Where User_Id = ?", (User.id,))
    Stats = Cursor.fetchone()
    
    if Stats:
        Msg = f"👤 Player Profile: {User.first_name}\n\n"
        Msg += f"⭐ Total Points: {Stats[0]}\n"
        Msg += f"🏆 Matches Won: {Stats[1]}\n"
        Msg += f"🎮 Games Played: {Stats[2]}\n"
    else:
        Msg = "Aapka Koi Data Nahi Mila. Pehle Ek Match Jeetiye! ⚡"
        
    await update.message.reply_text(Msg)

async def Help_Command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    Text = "Sahayata Menu:\n\n"
    Text += "/Lobby - Nayi Game Lobby Banayein\n"
    Text += "/Join - Game Mein Shamil Hone Ke Liye\n"
    Text += "/Start - Game Shuru Karne Ke Liye\n"
    Text += "/Profile - Apna Score Dekhne Ke Liye\n"
    Text += "/Rules - Game Ke Niyam Dekhein\n"
    Text += "/Guide - Khelne Ka Tarika Samjhein"
    await update.message.reply_text(Text)

async def Rules_Command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    Text = "Game Ke Niyam:\n\n"
    Text += "1. Clue Giver Kisi Bhi Taboo Word Ka Use Nahi Kar Sakta\n"
    Text += "2. Word Ka Tukda Ya Spelling Bolna Mana Hai\n"
    Text += "3. Galat Ishara Ya Acting Bhi Taboo Mani Jayegi\n"
    Text += "4. Sahi Guess Karne Par Team Ko 10 Points Milenge"
    await update.message.reply_text(Text)

async def Guide_Command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    Text = "Khelne Ka Tarika:\n\n"
    Text += "Step 1: Sabse Pehle /Lobby Banayein\n"
    Text += "Step 2: Sab Dost /Join Karein\n"
    Text += "Step 3: Creator /Start Dabayein\n"
    Text += "Step 4: Clue Giver Apne DM Mein Word Dekhe\n"
    Text += "Step 5: Baki Sab Group Mein Sahi Jawab Guess Karein"
    await update.message.reply_text(Text)

async def Warning_Timer1(chat_id, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(90)
    if Game_State["Is_Running"]:
        await context.bot.send_message(chat_id=chat_id, text="Jaldi Karein! Sirf 90 Seconds Baaki Hain! ⏳")

async def Warning_Timer2(chat_id, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(60)
    if Game_State["Is_Running"]:
        await context.bot.send_message(chat_id=chat_id, text="Jaldi Karein! Sirf 60 Seconds Baaki Hain! ⏳")

async def Warning_Timer3(chat_id, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(30)
    if Game_State["Is_Running"]:
        await context.bot.send_message(chat_id=chat_id, text="Jaldi Karein! Sirf 30 Seconds Baaki Hain! ⏳")

async def Warning_Timer4(chat_id, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(10) 
    if Game_State["Is_Running"]:
        await context.bot.send_message(chat_id=chat_id, text="Jaldi Karein! Sirf 10 Seconds Baaki Hain! ⏳")

async def Game_Status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not Game_State["Is_Running"]:
        await update.message.reply_text("Abhi Koi Game Nahi Chal Raha Hai! 🛌")
        return

    Msg = "📊 Current Game Status:\n\n"
    Msg += f"🔴 Team A Score: {Game_State['Scores']['A']}\n"
    Msg += f"🔵 Team B Score: {Game_State['Scores']['B']}\n"
    Msg += f"⏳ Current Turn: Team {Game_State['Current_Turn_Team']}\n"
    Msg += f"👤 Clue Giver: {Lobby_Data['Player_Names'][Game_State['Clue_Giver']]}"
    
    await update.message.reply_text(Msg)

async def Reset_Game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    User = update.message.from_user
    if User.id != Lobby_Data["Creator_Id"]:
        await update.message.reply_text("Sirf Creator Hi Game Reset Kar Sakta Hai! 🚫")
        return
        
    Game_State["Is_Running"] = False
    Lobby_Data["Is_Open"] = False
    await update.message.reply_text("Game Ko Puri Tarah Reset Kar Diya Gaya Hai! 🔄")

def Main():
    Token = "8380924465:AAFwbA-55qfkrA0-QJ_AL2uWuuS3Pt7y-Mw"
    
    App = ApplicationBuilder().token(TOKEN).connect_timeout(40).read_timeout(40).write_timeout(40).pool_timeout(40).build()
    
    App.add_handler(CommandHandler("Category", Set_Category))
    App.add_handler(CallbackQueryHandler(Handle_Category_Selection, pattern="^Cat_"))
    App.add_handler(CommandHandler("Lobby", Create_Lobby))
    App.add_handler(CommandHandler("Join", Join_Lobby))
    App.add_handler(CommandHandler("Leave", Leave_Lobby))
    App.add_handler(CommandHandler("Players", Show_Players))
    App.add_handler(CommandHandler("Cancel", Cancel_Lobby))
    App.add_handler(CommandHandler("Start", Start_Game))
    App.add_handler(CommandHandler("Next", Next_Round))
    App.add_handler(CommandHandler("Profile", My_Profile))
    App.add_handler(CommandHandler("Leaderboard", Show_Leaderboard))
    App.add_handler(CommandHandler("Help", Help_Command))
    App.add_handler(CommandHandler("Rules", Rules_Command))
    App.add_handler(CommandHandler("Guide", Guide_Command))
    App.add_handler(CommandHandler("Status", Game_Status))
    App.add_handler(CommandHandler("Reset", Reset_Game))
    
    App.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), Message_Referee))
    
    print("Taboo Bot Is Running... 🚀")
    App.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    Main()
