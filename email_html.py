import csv
import datetime

def get_listing_html(**kwargs) -> str:
    """
    Converts listing info to HTML list item that can be used in the e-mail HTML content.

    required input dict items:
    url: URL to listing web page.
    image_url: URL to listing image.
    address: Listing address.
    price: Listing price.
    n_rooms: Number of rooms.
    area_m2: Listing area in square meters.
    year_built: Listing construction date.
    date_added: Date listing was published.

    :return: String for HTML list item to be used in e-mail HTML.
    """

    # Format listing publishing date to a date string from epoch time
    date_added_datetime = datetime.datetime.fromtimestamp(float(kwargs["date_added"]))
    date_added = date_added_datetime.strftime("%Y-%m-%d %H:%M:%S%z")

    description_text = """\
    Price: {price} eur <br>
    Number of rooms: {n_rooms} <br>
    Area: {area_m2} m2 <br>
    Construction year: {year_built} <br>
    Date listed: {date_added}\
    """.format(
        price=kwargs["price"],
        n_rooms=kwargs["n_rooms"],
        area_m2=kwargs["area_m2"],
        year_built=kwargs["year_built"],
        date_added=date_added)

    listing_html = """\
    <li style="display: block; box-sizing: border-box; border-radius: 3px; text-align: left;\
    box-shadow: 1px 3px 1px 0 rgba(0, 0, 0, 0.08); border: 1px solid #cfcfcf; overflow: hidden;\
    background-color: #fff; font: normal 13px sans-serif; margin-bottom: 40px; max-width: 575px;">
        <a href="{listing_url}" style="float: left; width: 200px; height: 200px; display: block;\
        background-size: cover; background-image: url('{image_url}');">
        </a>
        <div style="float: left; box-sizing: border-box; max-width: 350px; padding: 30px;">
            <h2 style="font-size: 16px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin: 0;">
                <a href="{listing_url}" style="color: #2b2b2b; text-decoration: none;">
                    {address}
                </a>
            </h2>
            <p style="line-height: 20px; color: #5d5d5d; margin: 20px 0;">
                {description_text}
            </p>
        </div>
    </li>\
    """.format(
        listing_url=kwargs["url"],
        image_url=kwargs["image_url"],
        address=kwargs["address"],
        description_text=description_text)

    return listing_html


def get_email_html(listings: list) -> str:
    """
    Turns listing information to a HTML string for e-mail

    :param listings: List of dicts containing listing information.
    :return: HTML string for e-mail HTML body
    """

    listing_htmls = [get_listing_html(**listing) for listing in listings]
    html_list_items_string = "\n<br>\n".join(listing_htmls)

    email_html = """
    <html>
        <head>
            <title>Apartment listings</title>
        </head>
        <body>
            <ul class="article-list-vertical" style="list-style: none;\
             margin: 0 auto; max-width: 600px; text-align: center; padding: 0;">
                {list_items}
            </ul>
        </body>
    </html>
    """.format(list_items=html_list_items_string)

    return email_html


###########
# Testing #
###########

import csv
reader = csv.DictReader("""\
id,portal,active,url,image_url,address,n_rooms,area_m2,price,date_added,date_scraped,date_removed,year_built
2028821,c24,1,https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-kopli-tn/2960653,https://c24ee.img-bcg.eu/object/11/5191/2751785191.jpg,"Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Kopli tn 64-5",3,62.4,307944.0,1662132928,1669651864.8203578,0.0,1999
2083903,c24,1,"https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-kalaranna-21,/5576510",https://c24ee.img-bcg.eu/object/11/6377/1945436377.jpg,"Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Kalaranna 21, 23-49",3,64.2,340000.0,1665144388,1669651864.8204205,0.0,2000
2083899,c24,1,"https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-kalaranna-21,/1412295",https://c24ee.img-bcg.eu/object/11/6538/1614736538.jpg,"Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Kalaranna 21, 23-18",3,63.7,340000.0,1665144379,1669651864.820465,0.0,2001
2058893,c24,1,https://www.city24.ee/real-estate/apartments-for-sale/tallinn-pohja-tallinna-linnaosa-kopli-tn/2361067,https://c24ee.img-bcg.eu/object/11/9640/3083689640.jpg,"Harju maakond, Tallinn, Põhja-Tallinna linnaosa, Kopli tn 54",3,79.4,199000.0,1665411491,1669651864.8205063,0.0,2002\
""".splitlines())

listings = [item for item in reader]

print(get_email_html(listings))

# use: https://htmlemail.io/inline/


# TO DO:
# Reverse html heading (street & apt first)