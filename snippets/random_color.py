def rand_color(c):
    for i in range(8):
        color = []
        for _ in range(3):
            color.append(list(uos.urandom(1))[0])
        c[i] = (color[0], color[1], color[2])
