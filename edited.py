import flask
import os
import gmic
import numpy
import cv2
import base64
import hashlib
from PIL import Image

# Creating GMIC interpreter object
gmic_interpreter = gmic.Gmic()

app = flask.Flask(__name__)


def b64_to_cv2(base64_string):
    try:
        decoded_data = base64.b64decode(base64_string)

        hash_object = hashlib.sha256(decoded_data)
        r_hash = hash_object.hexdigest()
        buf = numpy.array(Image.open(decoded_data))
        # buf = numpy.frombuffer(decoded_data, dtype=numpy.uint8)
        cv2_img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return cv2_img, r_hash
    except Exception as e:
        print(e)


def acquired_saver(data, root="./"):
    time_dir_path = os.path.join(root, f"{data['Meta']['Date']}", f"{data['Meta']['Time']}")
    images_dir_path = os.path.join(time_dir_path, "Images")
    source_dir_path = os.path.join(time_dir_path, "Source")
    source_b_data_dir_path = os.path.join(source_dir_path, "B")
    source_p_data_dir_path = os.path.join(source_dir_path, "P")

    os.makedirs(images_dir_path, exist_ok=True)
    os.makedirs(source_b_data_dir_path, exist_ok=True)
    os.makedirs(source_p_data_dir_path, exist_ok=True)

    link_b = os.path.join(images_dir_path, f"{data['Meta']['Time']}_B.png")
    link_p = os.path.join(images_dir_path, f"{data['Meta']['Time']}_P.png")
    link_mask = os.path.join(images_dir_path, f"{data['Meta']['Time']}_Mask.png")

    cv2.imwrite(link_b, data["Images"]["B"])
    cv2.imwrite(link_p, data["Images"]["P"])
    try:
        cv2.imwrite(link_mask, data["Images"]["Mask"])
    except Exception as e:
        print(e)

    for light, values in data["Transport_Source"].items():
        for exposure, image in values.items():
            save_path = os.path.join(source_dir_path, light, f"{data['Meta']['Time']}_{light}_{exposure}.png")
            cv2.imwrite(save_path, image)

    return link_b, link_p, link_mask


def answer(data, b_image, p_image, b_link, p_link):
    answer_dict = {
        "Images": {
            "B": b_image,
            "P": p_image
        },
        "Links": {
            "B": b_link,
            "P": p_link,
            "Mask": ""
        },
        "Lost_Hashes": []
    }
    return answer_dict


@app.route('/upload/', methods=['POST'])
def upload():
    data = flask.request.get_json()
    if not data:
        return "No JSON data provided", 400
    else:
        print(len(data["Images"]['B']))
        data["Images"]["B"], r_hash = b64_to_cv2(data["Images"]["B"])
        data["R_Hash"]["Images"]["B"] = r_hash
        data["Images"]["P"], r_hash = b64_to_cv2(data["Images"]["P"])
        data["R_Hash"]["Images"]["P"] = r_hash
        try:
            data["Images"]["Mask"], r_hash = b64_to_cv2(data["Images"]["Mask"])
            data["R_Hash"]["Images"]["Mask"] = r_hash
        except:
            pass

        for light, values in data["Transport_Source"].items():
            for exposure, b64_image in values.items():
                data["R_Hash"]["Source"][light].setdefault(exposure, None)
                data["Transport_Source"][light][exposure], r_hash = b64_to_cv2(b64_image)
                data["R_Hash"]["Source"][light][exposure] = r_hash

        if data["Meta"]["Research"] == "gracia":
            gmic_image_list = []
            gmic_image_list.append(gmic.GmicImage.from_numpy(data["Images"]["B"]))
            gmic_image_list.append(gmic.GmicImage.from_numpy(data["Images"]["P"]))
            gmic_interpreter.run(f"{data['Gmic']}", gmic_image_list)
            data["Images"]["B"] = gmic_image_list[0].to_numpy()
            data["Images"]["P"] = gmic_image_list[1].to_numpy()
            data["Images"]["B"] = numpy.squeeze(data["Images"]["B"], axis=2)
            data["Images"]["P"] = numpy.squeeze(data["Images"]["P"], axis=2)

            gmic_interpreter.run(f"resize 300,300", gmic_image_list)
            resized_b_numpy = gmic_image_list[0].to_numpy()
            resized_b_numpy_sqieezed = numpy.squeeze(resized_b_numpy)
            byte_image = resized_b_numpy_sqieezed.tobytes()
            b64_image = base64.b64encode(byte_image)
            string_image_b = b64_image.decode('utf-8')

            resized_p_numpy = gmic_image_list[1].to_numpy()
            resized_p_numpy_sqieezed = numpy.squeeze(resized_p_numpy)
            byte_image = resized_p_numpy_sqieezed.tobytes()
            b64_image = base64.b64encode(byte_image)
            string_image_p = b64_image.decode('utf-8')
        else:
            string_image_b = None
            string_image_p = None

        if data["Hash"] == data["R_Hash"]:
            link_b, link_p, link_mask = acquired_saver(data, root=data["Root"])

            answ = answer(data, string_image_b, string_image_p, link_b, link_p)
            return flask.jsonify(answ), 200
        else:
            return flask.jsonify(answer(data)), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1515, debug=False)
