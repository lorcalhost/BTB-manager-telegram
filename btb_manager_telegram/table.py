def scientific_notation(nb, maxchar):
    nb_char = 6 if nb >= 0 else 7
    operator = "{:." + str(maxchar - nb_char) + "E}"
    ratio_srt = operator.format(nb).replace("E", "e")
    return ratio_srt


def float_strip(nb, maxchar):
    if maxchar < 8:
        raise NotImplementedError(
            "Tables does not support colum size of less than 8 for floats"
        )
    if nb == 0:
        return "0"
    int_part = "-" if nb < 0 else ""
    int_part += str(abs(int(nb)))
    float_part = abs(nb) - abs(int(nb))
    if len(int_part) > maxchar:
        return scientific_notation(nb, maxchar)
    if len(int_part) >= maxchar - 1:
        return str(int_part)
    float_part = round(float_part, maxchar - len(int_part) - 1)
    if abs(int(nb)) + float_part == 0:
        return scientific_notation(nb, maxchar)
    operator = "{:." + str(maxchar - len(int_part) - 1) + "f}"
    float_part = operator.format(float_part)[1:].rstrip(".0")
    return int_part + float_part


def string_srip(st, maxchar):
    if maxchar < 1:
        raise NotImplementedError(
            "Tables does not support colum size of less than 1 for strings"
        )
    if len(st) > maxchar:
        return st[: maxchar - 1] + "…"
    return st


def strip_data(data, maxchar):
    if type(data) in (float, int):
        return float_strip(data, maxchar)
    if type(data) == str:
        return string_srip(data, maxchar)
    else:
        raise NotImplementedError(f"Cannot handle data of type {str(type(data))}")


def fun_data_to_exact_size(data, size, add_spaces=True, align="left"):
    remove_size = 2 if add_spaces else 0
    data = strip_data(data, size - remove_size)
    nb_spaces = size - len(data)
    if align == "center":
        spaces_before = " " * (nb_spaces // 2)
        spaces_after = " " * (nb_spaces - nb_spaces // 2)
    elif align in ("left", "right"):
        spaces_before = " " * int(add_spaces)
        spaces_after = " " * (nb_spaces - int(add_spaces))
        if align == "right":
            spaces_after, spaces_before = spaces_before, spaces_after
    else:
        ValueError("'align' must be either 'center', 'left' or 'right'")
    return spaces_before + data + spaces_after


def data_to_exact_size(
    data, size, add_spaces=True, align="left", split_across_lines=False
):
    if split_across_lines:
        result = ""
        data = data.split(" ")
        index = 0
        while index < len(data):
            buffer = data[index]
            index += 1
            if index < len(data):
                while len(buffer + data[index]) < size:
                    buffer += " " + data[index]
                    index += 1
                    if index >= len(data):
                        break
            result += fun_data_to_exact_size(buffer, size, add_spaces, align)
            result += "\n" if index < len(data) else ""
        return result
    else:
        return fun_data_to_exact_size(data, size, add_spaces, align)


def fun_tabularize(col_head, col_data, col_size, add_spaces=True, align="left"):

    dash = "−"

    if type(align) is not list:
        align = [align] * len(col_head)

    if type(add_spaces) is not list:
        add_spaces = [add_spaces] * len(col_head)

    for i, size in enumerate(col_size):
        if size == 0:
            col_size[i] = (
                max(
                    [len(str(col_data[j][i])) for j in range(len(col_data[0]))]
                    + [len(str(col_head[i]))]
                )
                + 2
            )

    table = "```\n"

    table += "┌"
    for i, size in enumerate(col_size):
        if i > 0:
            table += "┬"
        table += dash * size
    table += "┐\n"

    col_head = [
        data_to_exact_size(
            header, col_size[i], add_spaces[i], align[i], split_across_lines=True
        ).split("\n")
        for i, header in enumerate(col_head)
    ]
    header_height = max([len(header) for header in col_head])

    for line in range(header_height):
        table += "│"
        for i, size in enumerate(col_size):
            if i > 0:
                table += "│"
            if line < len(col_head[i]):
                table += col_head[i][line]
            else:
                table += " " * size
        table += "│\n"

    table += "├"
    for i, size in enumerate(col_size):
        if i > 0:
            table += "┼"
        table += dash * size
    table += "┤\n"

    for j in range(len(col_data)):
        table += "│"
        for i, size in enumerate(col_size):
            if i > 0:
                table += "│"
            table += data_to_exact_size(col_data[j][i], size, add_spaces[i], align[i])
        table += "│\n"

    table += "└"
    for i, size in enumerate(col_size):
        if i > 0:
            table += "┴"
        table += dash * size
    table += "┘\n"

    table += "```\n"

    return table


def tabularize(heads, rows, sizes, add_spaces=True, align="left", nb_row=50):
    tables = []
    for i in range(len(rows) // nb_row + 1):
        tables.append(
            fun_tabularize(
                heads,
                rows[i * nb_row : i * nb_row + nb_row],
                sizes,
                add_spaces,
                align,
            )
        )
    return tables
