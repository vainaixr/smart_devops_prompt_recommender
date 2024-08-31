import polars as pl


def expanded_config():
    pl.Config(fmt_table_cell_list_len=10)
    pl.Config(fmt_str_lengths=5000)
    pl.Config.set_tbl_width_chars(3000)
    pl.Config(tbl_rows=50)
    pl.Config.set_tbl_cols(30)
