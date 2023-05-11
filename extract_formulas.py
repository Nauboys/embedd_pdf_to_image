from typing import List, Tuple

import PyPDF2

import regex as re

from wand.image import Image

import io

from pdfminer.layout import LAParams, LTTextBox
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator

import argparse

def check_formulas(list_of_formulas: List[str], text: str) -> bool:
    """
    Checking if the given text is in our formulas list

    Args:
        list_of_formulas (list): The list of formulas
        text (str): Text that was extracted from pdf
    Returns:
        bool : True if list contains the given string
               False if list does not contain
    """ 
    return any(text.replace(" ","") in formula.replace(" ","") or \
                formula.replace(" ","") in text.replace(" ","") \
                    for formula in list_of_formulas)  \




def check_new_box(old_ys: List[float], new_y: float) -> bool:
    """
    If the coordinate is close to the already 
    written list of coordinates, we assume it 
    corresponds to the same formula

    Args:
        old_ys (List[float]): The list of already found formulas coordination
        new_y (float): The coordination of the new found part of the formula
    Returns:
        bool : True if list contains similar coordinates
               False if list does not contain
    """ 
    return all(abs(old_y-new_y)>20 for old_y in old_ys) 



def create_image(pdf_one_page: PyPDF2._page.PageObject,box_coordination: Tuple[float, float, float, float],resolution: int, formula_num: int, page_num: int, width: float, height: float, output_location: str) -> None:
    """
    Creating the image of the formula

    Args:
        pdf_one_page (PyPDF2._page.PageObject): Pdf page where coordination should be taken of 
        box_coordination (List[List[float, float, float, float]])): Coordination of the boxes
        resolution (int): Resolution for resulting png in DPI.
        formula_num (int): Formula number
        page_num (int): Page number
        width (float): Width of the original pdf
        height (float): Height of the original pdf
        output_location (str): Location of the output should be save
    Returns:
        None
    """        
    dst_pdf = PyPDF2.PdfWriter()
    dst_pdf.add_page(pdf_one_page)

    pdf_bytes = io.BytesIO()
    dst_pdf.write(pdf_bytes)
    pdf_bytes.seek(0)

    img = Image(file = pdf_bytes, resolution = resolution,background = 'white')
    img.convert("png")
    
    file_name = f'{page_num}_page_{formula_num}_formula.png'
    constant_multi = 3
    print([int(box_coordination[0]), int(height - box_coordination[3]), int(box_coordination[2]), int(height - box_coordination[1])])
    img.resize(int(width)*constant_multi, int(height)*constant_multi)
    img.crop(int(box_coordination[0])*constant_multi, int(height - box_coordination[3])*constant_multi, 
        int(box_coordination[2])*constant_multi, int(height - box_coordination[1])*constant_multi)
    img.save(filename = output_location+file_name)



def box_coordiation_optimizing(coords:  List[Tuple[float, float, float, float]], max_width: float) -> List[Tuple[float, float, float, float]]:
    """
    Creating the list of the 4 coordinates for the 
    box drawing. We assume the following logic. We
    work with the y coordinates, and as formulas can
    expand in the x coordinate, but very small in the
    y coordinates. We are finding the y coordinates 
    with +-20 pixel and save the y coordinate. So 
    we can now have the y coordinate of the function
    and x will be the max,min of the pdf file

    Args:
        coords (List[Tuple[float, float, float, float]]): The list of tuples that contains coordinates
        max_width (float) : Max height of the pdf file
    Returns:
        List[Tuple[float, float, float, float]]) : Coordinates of each box that should be drawn
    """ 
    y_coords = []
    all_coords = []
    hyperparamter_similarity = 10
    for coord in coords:

        # in the 1st loop, we dont have coordinates
        if not y_coords:
            y_coords.append(coord[1])
            all_coords.append([0,coord[1]-hyperparamter_similarity,
                                max_width,coord[1]+hyperparamter_similarity+10])
            continue

        # in the next loops, we add the coordiante if its
        # not similar coordinates we have. 
        if check_new_box(y_coords,coord[1]):
            y_coords.append(coord[1])
            all_coords.append([0,coord[1]-hyperparamter_similarity,
                                max_width,coord[1]+hyperparamter_similarity+10])

    return all_coords




def pdf_box_coordination(pdf_name: str ,formulas: List[str], max_width: float) -> List[Tuple[float,float,float,float]]:
    """
    Creating the image of the formulas

    Args:
        pdf_name (str): The name of the 1page pdf file
        formulas (list): All formulas that should be in the file
        max_width (float) : Max height of the pdf file
    Returns:
        List[List[float,float,float,float]] : coordination of the boxes
    """
    
    # will be used to append all the formulas coordinates
    coords = []

    # Reading the pdf file
    fp = open(pdf_name, 'rb')
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    pages = PDFPage.get_pages(fp)
    # iterating over the 1 page
    for i,page in enumerate(pages):

        interpreter.process_page(page)
        layout = device.get_result()

        for lobj in layout:
            if isinstance(lobj, LTTextBox):
                # if the found text is in our found list of formulas
                # and the lenght is more than 2
                if check_formulas(formulas,lobj.get_text().strip().replace(" ","")) and \
                   len(lobj.get_text().strip())>2:
                    coords.append(lobj.bbox)

    all_coords = box_coordiation_optimizing(coords,max_width)

    return all_coords




def pdf_page_creation(src_pdf: PyPDF2._page.PageObject, page_num: int, formula_num: int) -> None:
    """
    Creating a 1 page pdf file with pagenumber and
    number of the formulas in the name

    Args:
        src_pdf (PyPDF2._page.PageObject): The pdf page that formula was found.
        page_num (int): Page number of the pdf where formula found.
        formula_num (int): Number of formulas that was found in the page
    Returns:
        None
    """
    dst_pdf = PyPDF2.PdfWriter()
    dst_pdf.add_page(src_pdf)

    with open(f'{page_num}_page_{formula_num}_formulas.pdf', 'wb') as f:
        dst_pdf.write(f)
        f.close()




def main():
    """Main function to execute the program."""

    # Parsing the arguments
    parser = argparse.ArgumentParser(description='Give the input file as pdf\
                                                  output will be images of formulas')
    parser.add_argument('input_pdf', type=str, help='Input pdf name')
    parser.add_argument('output_location', type=str, help='Output location')
    args = parser.parse_args()


    # Reading the file that was provided
    pdfFileObj = open(args.input_pdf, 'rb')
    pdfReader = PyPDF2.PdfReader(pdfFileObj)

    # for iteration over it
    number_pages = len(pdfReader.pages)
    formula_num = 0
    # we iterate over the pages of the given pdf files
    for page_num in range(number_pages):
        pageObj = pdfReader.pages[page_num]

        # Saving the width and height will be usefull
        # when we crop the pdf file
        media_box = pageObj.mediabox
        width = float(media_box.width)
        height = float(media_box.height)
        text = pageObj.extract_text()
        # When we have divide operation showed as line
        # it will extract as a new line element
        text = text.replace('\n', ' ')
        # print(text)
        # Regex to find the equations of the pdf file
        pattern = r"\b[\w]+\b[<>=]+[ ]*\([0-9+−*/∙()\w ]+\)[ 0-9+−*/∙()]*[%0-9+−*/∙ \wA-Za-z]*"
        matches = re.findall(pattern, text)
        if matches:
            # create the pdf file with the 1 page
            pdf_page_creation(pageObj, page_num = page_num,formula_num = len(matches)) 

            # cutting the formulas coordinates with rectangle
            box_coordinations  = pdf_box_coordination(f'{page_num}_page_{len(matches)}_formulas.pdf',matches, width)
            for ii,match in enumerate(matches):   
                formula_num += 1
                create_image(pageObj, box_coordinations[ii], 200, formula_num, page_num, width, height,args.output_location)



if __name__ == '__main__':
    
    main()