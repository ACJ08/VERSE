import re


def parse_call_sheet(text: str) -> dict:

    data = {
        "date": "",
        "production": "",
        "director": "",
        "location": "",
        "scenes": [],
        "cast": [],
        "crew": [],
        "shooting_time": ""
    }


    # Normalize extracted document text
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


    for line in lines:

        lower = line.lower()


        # Date
        if "date" in lower:
            parts = line.split("|")

            if len(parts) > 1:
                data["date"] = parts[-1].strip()


        # Production
        if "production" in lower:

            parts = line.split("|")

            if len(parts) > 1:
                data["production"] = parts[-1].strip()


        # Director
        if "director" in lower:

            parts = line.split("|")

            if len(parts) > 1:
                data["director"] = parts[-1].strip()


        # Location
        if "location" in lower:

            parts = line.split("|")

            if len(parts) > 1:
                data["location"] = parts[-1].strip()


        # Call time
        if "call" in lower or "shoot call" in lower:

            parts = line.split("|")

            for part in parts:

                if re.search(
                    r"\d{1,2}:\d{2}",
                    part
                ):
                    data["shooting_time"] = part.strip()



    # Extract scene numbers from schedule table

    for line in lines:

        if re.match(
            r"^\d+[A-Z]?\s*\|",
            line
        ):

            scene = line.split("|")[0].strip()

            data["scenes"].append(scene)



    # Extract CAST section

    capture = False

    for line in lines:

        if line.upper() == "CAST":
            capture = True
            continue


        if line.upper() == "CREW":
            capture = False


        if capture:
            data["cast"].append(line)



    # Extract CREW section

    capture = False

    for line in lines:

        if line.upper() == "CREW":
            capture = True
            continue


        if capture:
            data["crew"].append(line)



    return data