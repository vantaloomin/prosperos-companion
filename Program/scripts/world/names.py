"""Name banks for generated residents. Run `python scripts/world/names.py` to rewrite the shipped JSON.

Each bank is a set of groups, each with given names and family names that commonly go together. An underscore joins a two-word name. A city picks a
bank (by default from its era) and may weight the groups; real cities weight them by rough local estimates.
Lists favour ordinary names people actually had in the period and avoid stock fantasy names.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'companion' / 'world' / 'data' / 'names.json'


def group(feminine, masculine, neutral, family, cultures=None):
    made = {key: list(dict.fromkeys(word.replace('_', ' ') for word in words.split()))
            for key, words in (('feminine', feminine), ('masculine', masculine), ('neutral', neutral),
                               ('family', family))}
    return made | {'cultures': cultures or {}}


# How each modern heritage group takes given names from the popular names of the person's birth year
# (given_names.py). `local` is the city's own country (the United States for the built-in cities); a
# culture with its own family names supplies the family name too. The given-name lists below remain for
# settings outside those years.
CULTURES = {
    'anglo': {'local': 1},
    'black-american': {'us-black': 0.6, 'local': 0.4},
    'hispanic': {'us-hispanic': 0.6, 'local': 0.25, 'mexico': 0.15},
    'caribbean': {'jamaica': 0.4, 'haiti': 0.3, 'us-black': 0.3},
    'east-asian': {'local': 0.45, 'china': 0.15, 'korea': 0.12, 'vietnam': 0.12, 'philippines': 0.1, 'japan': 0.06},
    'south-asian': {'india': 0.65, 'local': 0.35},
    'jewish': {'local': 0.8, 'israel': 0.2},
    'italian': {'local': 0.8, 'italy': 0.2},
    'irish': {'local': 0.75, 'ireland': 0.25},
    'slavic': {'poland': 0.4, 'russia': 0.35, 'local': 0.25},
    'arabic': {'arab': 0.8, 'local': 0.2},
    'west-african': {'nigeria': 0.6, 'ghana': 0.4},
}


MODERN = {
    'anglo': group(
        'Emily Sarah Jessica Megan Lauren Hannah Abigail Rachel Katherine Molly Claire Allison Heather Amanda Erin '
        'Caroline Madison Paige Natalie Brooke',
        'Michael Matthew Ryan Andrew Tyler Kyle Brian Justin Jacob Benjamin Nathan Zachary Travis Cody Luke '
        'Daniel Adam Scott Colin Garrett',
        'Jordan Taylor Morgan Casey Riley Avery Quinn Parker',
        'Smith Johnson Miller Davis Wilson Anderson Taylor Thomas Moore Martin Thompson White Clark Lewis Walker '
        'Hall Allen Young King Wright Hill Green Baker Adams Nelson Carter Mitchell Roberts Turner Phillips Campbell '
        'Parker Evans Edwards Collins Stewart Morris Rogers Cook Bennett'),
    'black-american': group(
        'Aaliyah Jasmine Brianna Destiny Imani Kiara Tiana Ebony Monique Danielle Alexis Nia Janelle Keisha Simone '
        'Tamika Aisha Jada Kayla Shanice',
        'Marcus Darnell Jamal Terrence Andre Malik DeShawn Tyrone Isaiah Jalen Darius Cedric Elijah Xavier Corey '
        'Reginald Lamar Devin Jerome Maurice',
        'Jordan Cameron Peyton Sydney Kendall',
        'Washington Jefferson Jackson Robinson Harris Coleman Brooks Bryant Freeman Banks Gaines Dawson Mosley '
        'Carter Simmons Henderson Gibson Holloway Ellis Hayes Booker Pryor Battle Moton Tolliver'),
    'hispanic': group(
        'Maria Sofia Valentina Camila Daniela Gabriela Isabella Lucia Mariana Ximena Paola Adriana Veronica Yesenia '
        'Alejandra Catalina Elena Rosa Natalia Andrea',
        'Jose Luis Carlos Juan Miguel Alejandro Diego Javier Mateo Santiago Rafael Eduardo Andres Fernando Ricardo '
        'Hector Emilio Julio Ivan Raul',
        'Guadalupe Cruz Ariel Alexis',
        'Garcia Rodriguez Martinez Hernandez Lopez Gonzalez Perez Sanchez Ramirez Torres Flores Rivera Gomez Diaz '
        'Morales Reyes Cruz Ortiz Gutierrez Chavez Ramos Mendoza Ruiz Alvarez Castillo Jimenez Vargas Romero '
        'Herrera Medina Aguilar Vega Castro Delgado Navarro Fuentes Cabrera Espinoza Salazar Ibarra'),
    'caribbean': group(
        'Marjorie Nadege Shanelle Kerry-Ann Fabienne Roseline Tamara Natasha Chantal Sabrina Mirlande Shauna',
        'Jean Pierre Ricardo Fritz Damian Oneil Kemar Junior Wesley Dwayne Patrice Andre',
        'Rene Dominique Claude',
        'Joseph Pierre Jean-Baptiste Charles Louis Etienne Desir Baptiste Campbell Brown Williams Thompson Reid '
        'Francis Clarke Gordon Morgan Henry Barrett Grant'),
    'east-asian': group(
        'Grace Michelle Christine Jennifer Linda Amy Vivian Joyce Angela Mei Ji-woo Seo-yeon Yuki Hana Thao Linh '
        'Maricel Kristine Jasmine Lily',
        'Kevin Eric David Brian Steven Andrew Jason Daniel Ken Hiro Min-jun Ji-ho Wei Jun Minh Tuan Paolo '
        'Marlon Ryan Jonathan',
        'Kai Sam Jin',
        'Lee Kim Park Choi Chen Wang Li Zhang Liu Huang Wu Lin Nguyen Tran Le Pham Hoang Tanaka Suzuki Nakamura '
        'Yamamoto Santos Reyes Cruz Bautista Dela_Cruz Garcia Mendoza Villanueva'),
    'south-asian': group(
        'Priya Ananya Divya Neha Pooja Kavya Riya Shreya Aisha Fatima Meera Sana Anjali Nisha',
        'Arjun Rahul Vikram Rohan Sanjay Aditya Karthik Imran Omar Amit Nikhil Ravi Suresh Harpreet',
        'Kiran Sasha Arya',
        'Patel Shah Singh Kumar Sharma Gupta Reddy Rao Iyer Desai Mehta Joshi Chowdhury Khan Ahmed Malik Hussain '
        'Bhatt Menon Nair Kapoor Agarwal Gill Sandhu'),
    'jewish': group(
        'Rebecca Rachel Leah Miriam Hannah Shira Talia Naomi Ruth Ilana Dina Esther Abby Maya',
        'David Daniel Joshua Aaron Benjamin Noah Eli Ari Jonah Samuel Ethan Max Josh Adam',
        'Avi Shai',
        'Cohen Levy Goldberg Friedman Katz Schwartz Rosen Shapiro Klein Weiss Kaplan Stern Rosenberg Feldman '
        'Bernstein Horowitz Siegel Greenberg Adler Berman'),
    'italian': group(
        'Gina Theresa Angela Maria Francesca Nicole Christina Lisa Donna Gianna Marisa Teresa',
        'Anthony Vincent Joseph Dominic Salvatore Nicholas Frank Michael Carmine Paul Louis Joey',
        'Toni',
        'Russo Esposito Romano Ricci Marino Greco Bruno Gallo Conti DeLuca Costa Rizzo Lombardi Moretti Barbieri '
        'Fontana Caruso Ferrara Santoro Mancini'),
    'irish': group(
        'Kathleen Maureen Colleen Siobhan Bridget Erin Fiona Shannon Kelly Megan Nora Deirdre',
        'Patrick Sean Kevin Brendan Liam Connor Declan Brian Kieran Owen Ryan Dennis',
        'Shea Rory',
        "Murphy Kelly O'Brien Sullivan Walsh Byrne Ryan O'Connor McCarthy Doyle Gallagher Kennedy Lynch Quinn "
        "Fitzgerald Brennan Donnelly Flanagan Kavanagh Callahan"),
    'slavic': group(
        'Katarzyna Anna Natalia Olga Irina Svetlana Ewa Magdalena Tatiana Yelena Agnieszka Daria',
        'Piotr Tomasz Pavel Dmitri Sergei Andrzej Marek Viktor Mikhail Stefan Bogdan Lukasz',
        'Sasha',
        'Kowalski Nowak Wisniewski Lewandowski Zielinski Kaminski Novak Petrov Ivanov Sokolov Volkov Popov '
        'Kovalenko Shevchenko Horvat Kozlowski Mazur Bondarenko'),
    'arabic': group(
        'Layla Nour Mariam Yasmin Rania Huda Salma Dalia Amira Zeinab Lina Hala',
        'Ahmed Mohamed Omar Khalid Youssef Karim Tariq Samir Hassan Ali Bilal Nabil',
        'Noor Rayan',
        'Haddad Khoury Nasser Saleh Hamdan Mansour Aziz Farah Rahman Abdullah Ibrahim Hassan Darwish Kassem Bakri'),
    'west-african': group(
        'Chiamaka Adaeze Ngozi Folake Amara Ifeoma Abena Ama Efua Yewande Kemi Zainab',
        'Chinedu Emeka Oluwaseun Tunde Kwame Kofi Kwabena Obinna Femi Ibrahima Moussa Segun',
        'Tobi Ayo',
        'Okafor Okonkwo Adeyemi Balogun Mensah Asante Owusu Boateng Diallo Traore Nwosu Eze Adebayo Ogunleye '
        'Danso Ndiaye'),
}

for key, links in CULTURES.items():
    MODERN[key]['cultures'] = links

VICTORIAN = {
    'english': group(
        'Mary Elizabeth Sarah Annie Alice Florence Emily Edith Ellen Ada Clara Harriet Louisa Martha Jane Emma '
        'Lucy Rose Kate Beatrice Agnes Lilian Violet Mabel Ethel',
        'William John George Thomas James Charles Henry Frederick Arthur Albert Alfred Walter Joseph Edward '
        'Robert Samuel Ernest Herbert Harry Richard Francis Percy Sidney Frank Edwin',
        '',
        'Smith Jones Williams Taylor Brown Davies Wilson Evans Thomas Johnson Roberts Robinson Wright Wood Hall '
        'Green Walker Hughes Edwards Lewis Turner Jackson Harris Clarke Cooper Ward Morris King Baker Harrison '
        'Allen Mitchell Hill Parker Price Bennett Cox Fletcher Pearce Webb Holloway Marsh Pritchard'),
    'irish': group(
        'Bridget Catherine Margaret Honora Ellen Mary Johanna Nora Kate Julia',
        'Patrick Michael John Daniel Timothy Cornelius Dennis Thomas Jeremiah Owen',
        '',
        "Sullivan Murphy O'Brien Kelly Driscoll Connell Mahony Callaghan Doyle Byrne Flynn Brennan"),
    'scottish': group(
        'Jessie Isabella Christina Janet Agnes Margaret Euphemia Marion Grace Helen',
        'Alexander Duncan Hugh Angus Donald Archibald Malcolm Robert Andrew David',
        '',
        'Macdonald Campbell Stewart Robertson Murray Fraser Grant Reid Cameron Ross Henderson Paterson'),
    'jewish': group(
        'Rachel Leah Rebecca Esther Hannah Miriam Rosa Fanny Sophia Betsy',
        'Isaac Samuel Moses Solomon Abraham Joseph Lewis Nathan Benjamin Hyman',
        '',
        'Cohen Levy Isaacs Jacobs Hart Moss Abrahams Myers Solomon Lazarus Goldsmith Mendoza'),
    'italian': group(
        'Maria Giuseppina Rosa Teresa Angela Lucia Carmela',
        'Giuseppe Antonio Giovanni Luigi Pietro Carlo Domenico',
        '',
        'Ricci Bianchi Gatti Ferrari Costa Ortelli Gazzi Negretti'),
    'west-riding': group(
        'Hannah Martha Sarah Ann Mary Ellen Elizabeth Alice Emma Ruth Phoebe Mercy Esther Annie Ada Polly '
        'Edith Lizzie',
        'John William Joseph James Thomas George Samuel Benjamin Abraham Jonas Joshua Eli Fred Harold Albert '
        'Walter Tom Ned',
        '',
        'Sugden Ackroyd Holroyd Greenwood Sutcliffe Crowther Haigh Hirst Barraclough Firth Ramsden Wadsworth '
        'Butterworth Normanton Brearley Hinchliffe Pickles Shackleton Mitchell Booth Lumb Priestley Wormald '
        'Ingham Rushworth Dobson'),
}

MEDIEVAL = {
    'norman': group(
        'Alice Isabel Matilda Joan Margery Agnes Emma Juliana Petronilla Avice Cecily Rohese Sybil Beatrice '
        'Eleanor Mabel',
        'William Robert Richard Ralph Hugh Walter Geoffrey Roger Gilbert Henry Simon Thomas Nicholas Baldwin '
        'Reginald Guy',
        '',
        'de_Clare de_Lacy Mortimer Peverel Basset Beauchamp Mandeville Giffard Clifford Malet Ferrers Talbot'),
    'english': group(
        'Agnes Alice Maud Edith Joan Emma Margery Christina Godiva Elfrida Wymarc Ellen Annot Tibb Mariot',
        'John Thomas Adam Walter Wat Hob Robin Peter Simkin Edwin Godric Alfred Osric Wulfric Tom Dickon',
        '',
        'Atwood Miller Smith Baker Fletcher Carter Thatcher Webster Brewer Cooper Turner Shepherd Fisher Wright '
        'Chapman Mason Ward Fowler Gardner Bowyer'),
    'welsh': group(
        'Gwen Angharad Nest Gwenllian Morfudd Eluned Tangwystl Lleucu',
        'Dafydd Rhys Owain Gruffudd Madog Iorwerth Llywelyn Hywel',
        '',
        'ap_Rhys ap_Owain ferch_Madog Gwyn Llwyd Vychan Goch Ddu'),
}

FRONTIER = {
    'american': group(
        'Mary Sarah Martha Hattie Lizzie Nancy Lucinda Mattie Emma Ida Josephine Belle Clara Laura Minnie Sadie '
        'Cora Nellie Pearl Effie',
        'John James William George Charles Henry Thomas Samuel Joseph Wyatt Jesse Amos Silas Lafayette Elijah '
        'Ezra Calvin Ben Lem Jim',
        '',
        'Clanton Hughes Bradshaw Pruitt Tolliver Haskell Whitfield Gentry Burris Coffey Rutledge Spence Dunlap '
        'Crenshaw Harlan Fenton Rhodes McKinney Baird Bascom Puckett Yancey'),
    'mexican': group(
        'Maria Josefa Refugio Guadalupe Dolores Manuela Juana Soledad Petra Ramona Trinidad Carmen',
        'Jose Juan Manuel Francisco Jesus Ignacio Pedro Ramon Antonio Santiago Esteban Rafael',
        '',
        'Romero Elias Ochoa Pacheco Ortiz Telles Leon Aguirre Robles Samaniego Contreras Salazar Montoya'),
    'cornish': group(
        'Jenefer Mary Elizabeth Grace Thomasine Loveday Jane Kitty',
        'John Richard William Nicholas Josiah Hart Jabez Thomas Samuel Edward',
        '',
        'Trevithick Penrose Polglase Tregear Pascoe Trelawny Nankivell Rowe Bolitho Pengelly Tremayne Chenoweth'),
    'irish': group(
        'Bridget Mary Margaret Annie Kate Nora Ellen',
        'Patrick Michael Dennis Timothy Cornelius Owen Daniel',
        '',
        "O'Rourke Sweeney Daly Hogan Mahoney Riordan Cassidy Moran"),
    'german': group(
        'Anna Katharina Margaretha Elisabeth Louisa Wilhelmina Emma',
        'Johann Friedrich Heinrich Wilhelm Karl August Otto',
        '',
        'Schmidt Becker Vogel Hartmann Kessler Lutz Brunner Weber Zimmermann'),
    'chinese': group(
        'Ah_Ying Mei_Lan Gum_Moy Sing_Toy Lai_Ho',
        'Ah_Sam Wing Chung Fook Quong Hop_Kee Sing',
        '',
        'Lee Wong Chan Chin Yee Ng Fong Louie'),
}

STORYBOOK = {
    'plain': group(
        'Hester Marigold Tansy Prudence Wilhelmina Bettony Dulcie Maud Clover Ottilie Hazel Posy Clemency Ada '
        'Bryony Winnie Lettice Petunia Tibby Gwendolyn',
        'Tobin Bram Hob Wendel Barnaby Ambrose Jory Ned Ferris Osgood Pip Cuthbert Dunstan Rollo Jasper Ezekiel '
        'Lem Horace Bartholomew Wilbur',
        'Robin Wren Ash Sorrel',
        'Thistlewood Bramblecot Greenhollow Puddifoot Hobbs Mossley Applegarth Tumblestone Wickham Fennimore '
        'Butterbridge Larkspur Crumb Featherstone Tillbrook Underhay Copperkettle Pennywhistle Oakshott Fairweather'),
}

BANKS = {'modern': MODERN, 'victorian': VICTORIAN, 'medieval': MEDIEVAL, 'frontier': FRONTIER, 'storybook': STORYBOOK}

NAMES = {
    'schema_version': 1,
    'source': {'kind': 'curated', 'title': 'Name banks written for Prospero Companion', 'license': 'CC0-1.0',
               'retrieved': '2026-10-05',
               'note': 'Common given and family names by period and heritage, from general knowledge, for fiction. '
                       'Group weights for real cities are rough estimates, not census figures.'},
    'banks': BANKS,
    # The bank a city uses when it names none, and the group weights it starts from.
    'eras': {
        'modern': {'bank': 'modern', 'mix': {'anglo': 4, 'black-american': 1.5, 'hispanic': 2, 'east-asian': 0.7,
                                             'south-asian': 0.5, 'jewish': 0.4, 'italian': 0.5, 'irish': 0.5,
                                             'slavic': 0.3, 'arabic': 0.3, 'west-african': 0.2, 'caribbean': 0.2}},
        'future': {'bank': 'modern', 'mix': {}},
        'other': {'bank': 'modern', 'mix': {}},
        'victorian': {'bank': 'victorian', 'mix': {'english': 8, 'irish': 1.5, 'scottish': 1, 'jewish': 0.6,
                                                   'italian': 0.3}},
        'steampunk': {'bank': 'victorian', 'mix': {'west-riding': 8, 'english': 2, 'irish': 1.5, 'scottish': 0.5}},
        'medieval': {'bank': 'medieval', 'mix': {'english': 6, 'norman': 2, 'welsh': 1}},
        'frontier': {'bank': 'frontier', 'mix': {'american': 6, 'mexican': 3, 'cornish': 1.5, 'irish': 1.5,
                                                 'german': 1, 'chinese': 0.6}},
        'fantasy': {'bank': 'storybook', 'mix': {}},
    },
}

if __name__ == '__main__':
    OUT.write_text(json.dumps(NAMES, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}')
