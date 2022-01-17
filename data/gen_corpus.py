BASE_FNAME = "full_dict.txt"
OUT_FORMAT = "length{}.txt"

def main():
    fs = {}
    with open(BASE_FNAME, 'r') as f:
        for line in f:
            word = line.strip().lower()
            l = len(word)
            if l not in fs:
                fs[l] = open(OUT_FORMAT.format(l), 'w')
            print(word, file=fs[l])
    for fobj in fs.values():
        fobj.close()


if __name__ == "__main__":
    main()

