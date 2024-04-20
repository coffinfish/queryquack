import pdfreaderclass as pr
if __name__ == "__main__":
    qq = queryquack = pr.pdfreaderclass("quackery")
    print(qq.loadPDF("Stallings William - Operating Systems_ Internals and Design Principles (2018, Pearson Education) - libgen.li.pdf", "CPS590"))
    qq.setCurrentNamespace("CPS590")
    t = open("cps590test.txt", "wb")
    
    t.write(qq.ask("Can you generate me 77 multiple choice questions. 28 from Chapter 5, 24 from Chapter 6 (excluding 6.9, 6.10, 6.11), 7 from Chapter 7 (excluding 7A), and 17 from Chapter 8 (excluding 8.3, 8.5, 8.6, and the part of 8.4 on Linux Page Replacement post release 2.6.28). 25 of the multiple choice questions are multiple select. All multiple choie questions have an option e) None of the above, and only some multiple select questions have the option e) None of the above."))
    
    t.close()