import pandas as pd

# Data for the table
data = [
    {"user": "liv_offial", "FullName": "Mindset Coach|Transformation Program", "First Name": "Mindset", "Instagram Link": "", "Followers": ""},
    {"user": "inspirelegacycr", "FullName": "Inspire Legacy Coaching & Retreats", "First Name": "Inspire", "Instagram Link": "", "Followers": ""},
    {"user": "moneymindsethub", "FullName": "CARLA TOWNSEND • Money Mindset Mentor", "First Name": "CARLA", "Instagram Link": "", "Followers": ""},
    {"user": "coach_niharika", "FullName": "Niharika Sethi", "First Name": "Niharika", "Instagram Link": "", "Followers": ""},
    {"user": "nataliebcoaching", "FullName": "Natalie Barratt Coach", "First Name": "Natalie", "Instagram Link": "", "Followers": ""},
    {"user": "relindemoors", "FullName": "Serve Boldly, Succeed Wildly", "First Name": "Relinde", "Instagram Link": "https://www.instagram.com/relindemoors", "Followers": "10+ likes"},
    {"user": "ludmilapalhano.psiquiatra", "FullName": "The Health CEO Academy", "First Name": "Ludmila", "Instagram Link": "https://www.instagram.com/ludmilapalhano.psiquiatra", "Followers": "5 likes"},
    {"user": "namulwany", "FullName": "Melanie Hapisu - Wambugu", "First Name": "Melanie", "Instagram Link": "https://www.instagram.com/namulwany", "Followers": "10+ likes"},
    {"user": "chamtangofficial", "FullName": "Cham Tang", "First Name": "Cham", "Instagram Link": "https://www.instagram.com/chamtangofficial", "Followers": "10+ likes"},
    {"user": "toni_everard", "FullName": "Toni Everard | Business Coach", "First Name": "Toni", "Instagram Link": "https://www.instagram.com/toni_everard", "Followers": "9 likes"},
    {"user": "teacherprix", "FullName": "Priscila Pereira", "First Name": "Priscila", "Instagram Link": "https://www.instagram.com/teacherprix", "Followers": "140+ likes"},
    {"user": "ed.paget", "FullName": "Ed Paget", "First Name": "Ed", "Instagram Link": "https://www.instagram.com/ed.paget", "Followers": "20+ likes"},
    {"user": "yg_thecareergem", "FullName": "Yanira Guzman", "First Name": "Yanira", "Instagram Link": "https://www.instagram.com/yg_thecareergem", "Followers": "7 likes"},
    {"user": "j.t.odonnell", "FullName": "J.T. O'Donnell", "First Name": "J.T.", "Instagram Link": "https://www.instagram.com/j.t.odonnell", "Followers": "10+ likes"},
    {"user": "ronnie.built.that", "FullName": "Ronnie", "First Name": "Ronnie", "Instagram Link": "https://www.instagram.com/ronnie.built.that", "Followers": "9 likes"},
    {"user": "yamileetoussaint", "FullName": "Yamilee Toussaint", "First Name": "Yamilee", "Instagram Link": "https://www.instagram.com/yamileetoussaint", "Followers": "10+ likes"},
    {"user": "iammichellecaba", "FullName": "Michelle Caba", "First Name": "Michelle", "Instagram Link": "https://www.instagram.com/iammichellecaba", "Followers": "40+ likes"},
    {"user": "dorthahise", "FullName": "Dortha Hise", "First Name": "Dortha", "Instagram Link": "https://www.instagram.com/dorthahise", "Followers": "4 likes"},
    {"user": "simplyfiercely", "FullName": "Simply Fiercely", "First Name": "Simply", "Instagram Link": "https://www.instagram.com/simplyfiercely", "Followers": "20+ likes"},
    {"user": "sean_gallagher_photo", "FullName": "Sean Gallagher", "First Name": "Sean", "Instagram Link": "https://www.instagram.com/sean_gallagher_photo", "Followers": "20+ likes"},
    {"user": "joyful_selling_for_creatives", "FullName": "Joyful Selling for Creatives", "First Name": "Joyful", "Instagram Link": "https://www.instagram.com/joyful_selling_for_creatives", "Followers": "10+ likes"},
    {"user": "youthoffthestreets", "FullName": "Youth Off The Streets", "First Name": "Youth", "Instagram Link": "https://www.instagram.com/youthoffthestreets", "Followers": "20+ likes"},
    {"user": "lifeatibm", "FullName": "Life at IBM", "First Name": "Life", "Instagram Link": "https://www.instagram.com/lifeatibm", "Followers": "610+ likes"},
    {"user": "louise_badasscoaching", "FullName": "Louise O Brien | Online Coach", "First Name": "Louise", "Instagram Link": "https://www.instagram.com/louise_badasscoaching", "Followers": "20+ likes"},
    {"user": "zachmentalloadcoach", "FullName": "Zach Watson M. Ed.", "First Name": "Zach", "Instagram Link": "https://www.instagram.com/zachmentalloadcoach", "Followers": "1.3K+ likes"},
    {"user": "ruthysonntag", "FullName": "Ruthy Sonntag | Master Certified Life Coach", "First Name": "Ruthy", "Instagram Link": "https://www.instagram.com/ruthysonntag", "Followers": "2 likes"},
    {"user": "showupsociety", "FullName": "Tammie Bennett | Mindset Coach", "First Name": "Tammie", "Instagram Link": "https://www.instagram.com/showupsociety", "Followers": "90+ likes"},
    {"user": "coachkarfei", "FullName": "Coach Karfei", "First Name": "Karfei", "Instagram Link": "https://www.instagram.com/coachkarfei", "Followers": "100+ likes"},
]

# Create a DataFrame and save it as a CSV file
df = pd.DataFrame(data)
df.to_csv("combined_instagram_data.csv", index=False)
print("Data saved as combined_instagram_data.csv")
