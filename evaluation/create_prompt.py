from utils.prompting import create_conversation

desc = open("./testfiles/long/01.txt", "r").read()

prompt = create_conversation(desc)[0]['content']

print(prompt)