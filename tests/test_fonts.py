# from InkGen.fonts import FontFinder
# import pytest
# import os

# @pytest.mark.skip
# def test_create_fontfinder():
#     ff = FontFinder()
#     assert len(list(ff.fonts)) > 0
#     assert "bold" in ff.font_styles("Times New Roman")
#     assert "italic" in ff.font_styles("Times New Roman")
#     assert "regular" in ff.font_styles("Times New Roman")
#     assert "bold italic" in ff.font_styles("Times New Roman")
#     assert os.path.basename(ff.font_path("Times New Roman", "Regular")) == "times.ttf"
#     assert "regular" in ff.font_info("Times New Roman").keys()
#     assert "bold" in ff.font_info("Times New Roman").keys()
#     assert "italic" in ff.font_info("Times New Roman").keys()
#     assert "bold italic" in ff.font_info("Times New Roman").keys()
#     expected_keys = ["Full Name", "Typographic Family", "Typographic Subfamily", "File Path"]
#     assert list(ff.font_info("Times New Roman")['bold italic'].keys()) == expected_keys
#     assert list(ff.font_info("Times New Roman", 'bold italic').keys()) == expected_keys

# def test_specify_font_path():
#     ff = FontFinder(["C:\\Windows\\Fonts"])
#     assert len(list(ff.fonts)) > 0

#     with pytest.raises(ValueError):
#         ff = FontFinder(["C:\\Windows\\Fontina"])

# def test_font_family_errors():
#     ff = FontFinder()
#     with pytest.raises(ValueError):
#         ff.font_styles("Times New Reagan")
#     with pytest.raises(ValueError):
#         ff.font_path("Times New Reagan")
#     with pytest.raises(ValueError):
#         ff.font_info("Times New Reagan")

# def test_font_style_errors():
#     ff = FontFinder()
#     with pytest.raises(ValueError):
#         ff.font_path("Times New Roman", "Regluated")
#     with pytest.raises(ValueError):
#         ff.font_info("Times New Roman", "Regluated")

# @pytest.mark.skip
# def test_font_checks():
#     ff = FontFinder()

#     assert ff.font_exists("Times New Roman")
#     assert not ff.font_exists("Times New Reagan")

#     assert ff.style_exists("Times New Roman", "Regular")
#     assert not ff.style_exists("Times New Roman", "Regulated")
#     with pytest.raises(ValueError):
#         ff.style_exists("Times New Reagan", "Regular")
