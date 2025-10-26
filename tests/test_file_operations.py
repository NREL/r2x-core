from r2x_core.utils.file_operations import backup_folder


def test_backup_folder(tmp_path, caplog):
    tmp_folder = tmp_path / "folder"

    tmp_folder.mkdir()
    fpath = tmp_folder / "test.txt"
    fpath.write_text("Hello")

    result = backup_folder(tmp_folder)

    assert result.is_ok()

    assert (tmp_folder.parent / "folder_backup").exists()

    result = backup_folder(tmp_folder)
    assert "exists" in caplog.text
