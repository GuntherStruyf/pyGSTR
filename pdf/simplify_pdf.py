
import base64
import io
import os
import subprocess
import shlex
from matplotlib import pyplot as plt
import matplotlib.image as mpimg
import xml.etree.ElementTree as ET
import numpy as np
import cv2
from tqdm import tqdm
import sys

XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
INKSCAPE_EXE = 'C:/Program Files/Inkscape/inkscape.exe'
assert os.path.exists(INKSCAPE_EXE), f'Inkscape ({INKSCAPE_EXE}) not found.'


def query_yes_no(question, default='yes'):
    """
    Ask a yes/no question via raw_input() and return their answer.

    'question' is a string that is presented to the user.
    'default' is the presumed answer if the user just hits <Enter>.
        It must be 'yes' (the default), 'no' or None (meaning
        an answer is required of the user).

    The 'answer' return value is True for 'yes' or False for 'no'.
    """
    valid = {'yes': True, 'y': True, 'ye': True,
             'no': False, 'n': False}
    if default is None:
        prompt = ' [y/n] '
    elif default == 'yes':
        prompt = ' [Y/n] '
    elif default == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError(f'invalid default answer: \'{default}\'')

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print('Please respond with \'y(es)\' or \'n(o)\' '
                  '(or \'y\' or \'n\').\n')


def get_href(tag):
    return tag.attrib[XLINK_HREF]


def get_tag_image(tag):
    data = get_href(tag)
    if data.startswith('data:image'):
        seps = []
        seps.append(data.find('/', 0))
        seps.append(data.find(';', seps[-1]))
        seps.append(data.find(',', seps[-1]))
        img_type = data[seps[0] + 1:seps[1]]  # pylint: disable=unused-variable  # noqa: F841, E501
        base = data[seps[1] + 1:seps[2]]
        assert base == 'base64'
        data = data[seps[-1] + 1:]
    # else assume base 64
    byte_img = base64.b64decode(data)
    io_bytes = io.BytesIO(byte_img)
    return mpimg.imread(io_bytes, format='PNG')


def show_img(img, *args, **kwargs):
    plt.imshow(img)
    plt.show(*args, **kwargs)


def show_svg_image(tag):
    img = get_tag_image(tag)
    show_img(img)


def is_same_imgs(a, b):
    if a.ndim != b.ndim:
        return False
    # use smallest image as template, other as image
    if a.size > b.size:
        image = a
        templ = b
    else:
        image = b
        templ = a
    # limit templ width/height to image width/height
    shp = image.shape
    if templ.ndim == 2:
        templ = templ[:shp[0], :shp[1]]
    elif templ.ndim == 3:
        templ = templ[:shp[0], :shp[1], :]
    else:
        raise NotImplementedError

    r = cv2.matchTemplate(image, templ, cv2.TM_SQDIFF_NORMED)
    return np.min(r) < 1e-4


def img_to_rgb_list(img):
    # assume rgb image with optional alpha
    # strip alpha + reshape into Nx3 matrix
    return img[:, :, :3] .reshape((-1, 3))


def img_std_color(img):
    return np.std(img_to_rgb_list(img), axis=0)


def img_avg_color(img):
    return np.mean(img_to_rgb_list(img), axis=0)


def get_namespaces(xml_file):
    with open(xml_file, 'r') as f:
        xml_data = f.read()
        xml_iter = ET.iterparse(io.StringIO(xml_data), events=['start-ns'])
        return dict([node for _, node in xml_iter])


def register_all_namespaces(xml_file):
    for k, v in get_namespaces(xml_file).items():
        print(f'Register \'{k}\':{v}')
        ET.register_namespace(k, v)


def pdf_to_svg(pdf_path: str, svg_path: str):
    assert os.path.exists(pdf_path), f'PDF ({pdf_path}) not found.'
    assert not os.path.exists(svg_path), f'SVG ({svg_path}) already exists.'
    print('Inkscape convert pdf > svg')
    cmd = f'"{INKSCAPE_EXE}" --without-gui --file="{pdf_path}" ' + \
        f'--export-plain-svg="{svg_path}"'
    print(f'Inkscape convert svg > pdf: {cmd}')
    subprocess.call(shlex.split(cmd))


def svg_to_pdf(svg_path: str, pdf_path: str):
    assert os.path.exists(svg_path), f'SVG ({svg_path}) not found.'
    assert not os.path.exists(pdf_path), f'PDF ({pdf_path}) already exists.'
    cmd = f'"{INKSCAPE_EXE}" --without-gui --file="{svg_path}" ' + \
        f'--export-pdf="{pdf_path}"'
    print(f'Inkscape convert svg > pdf: {cmd}')
    subprocess.call(shlex.split(cmd))


def calc_color_alpha(background_clr, foreground_clr, alpha: float):
    return alpha * foreground_clr + (1 - alpha) * background_clr


def clone_copies(svg):
    image_tags = svg.findall('.//{http://www.w3.org/2000/svg}image')

    # list of tags to keep, item=Tuple(tag, image)
    keep_tags = []
    # list of tags to be cloned, item=Tuple(tag,
    #                                       index of keep_tags to clone from)
    clone_tags = []
    for tag1 in tqdm(image_tags):
        img1 = get_tag_image(tag1)
        for keep_idx, (keep_tag, keep_img) in enumerate(keep_tags):
            if is_same_imgs(img1, keep_img):
                if img1.size > keep_img.size:
                    # new image is larger, replace the keep-image
                    keep_tags[keep_idx] = (tag1, img1)
                    # and add the previous keep-tag one as a clone
                    clone_tags.append((keep_tag, keep_idx))
                else:
                    clone_tags.append((tag1, keep_idx))
                break
        else:
            keep_tags.append((tag1, img1))

    # replace the duplicate elements with clones
    for clone_tag, ref_idx in clone_tags:
        # get the id of the tag that we keep
        ref_id = keep_tags[ref_idx][0].attrib['id']
        # and replace the clone tag with a "use<id>" tag
        clone_tag.tag = 'use'
        clone_tag.attrib[XLINK_HREF] = f'#{ref_id}'


    # if necessary, also replace original tag by a rect of one color
    for keep_tag, img in keep_tags:
        show_img(img, block=False)
        plt.pause(1.5)
        plt.close()
        if query_yes_no('Replace image with flat color?', default='no'):
            keep_tag.tag = 'rect'
            clr = img_avg_color(img)
            if query_yes_no('Custom opacity?'):
                sys.stdout.write('Input opacity [float]:')
                opacity = float(input())
                # pdf with opacity not 1.0 is slow to render
                # more simple to just change the color
                white = np.full(3, 255)
                clr = calc_color_alpha(white, clr, opacity)
            clr_hex = '#' + ''.join([f'{int(np.round(clrii)):02x}'
                                    for clrii in clr[:3]])
            keep_tag.attrib['style'] = \
                f'fill:{clr_hex};fill-opacity:1.0;stroke:none;' + \
                f'stroke-width:1.5;stroke-miterlimit:4;' + \
                f'stroke-dasharray:none;stroke-opacity:1'
            for attr in [XLINK_HREF, 'transform', 'preserveAspectRatio']:
                keep_tag.attrib.pop(attr)


script_dir = os.path.dirname(__file__)
xml_filepath = os.path.join(script_dir, 'file3.svg')
register_all_namespaces(xml_filepath)

xml = ET.parse(xml_filepath)
svg = xml.getroot()
clone_copies(svg)
xml.write('output-file3.svg')

pdf_output = os.path.join(script_dir, 'testauto3.pdf')
if os.path.exists(pdf_output):
    os.remove(pdf_output)
svg_to_pdf(os.path.join(script_dir, 'output-file3.svg'), pdf_output)
