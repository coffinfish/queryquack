import pdfreaderclass as pr
if __name__ == "__main__":
    qq = pr.pdfreaderclass("quackery")
    while (userInput := input("")) != "quit":
        print(qq.ask(userInput))