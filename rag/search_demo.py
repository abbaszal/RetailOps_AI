from search import search, format_context

if __name__ == "__main__":
    q = "Can I return an item after 14 days? What about VIP?"
    hits = search(q, k=5)
    print(format_context(hits))
