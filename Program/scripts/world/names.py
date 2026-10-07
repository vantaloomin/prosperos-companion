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
        'Bridget Catherine Margaret Honora Ellen Mary Johanna Nora Kate Julia Anne Winifred Eliza Sarah '
        'Elizabeth Annie Teresa Agnes Alice Delia Sabina Abina Kitty Hannah Jane Rose Josephine Maggie Lizzie '
        'Bessie Christina Susan',
        'Patrick Michael John Daniel Timothy Cornelius Dennis Thomas Jeremiah Owen James William Edward '
        'Bartholomew Florence Terence Hugh Martin Peter Francis Joseph Bernard Matthew Laurence Christopher '
        'Andrew Charles Edmund Richard Maurice Thady Myles Felix',
        '',
        "Sullivan Murphy O'Brien Kelly Driscoll Connell Mahony Callaghan Doyle Byrne Flynn Brennan Ryan Walsh "
        "O'Neill Kennedy McCarthy Donovan Leary Regan Kavanagh Fitzgerald Burke Hayes Carroll Nolan Keane Quinn "
        "Daly Healy Kearney Moriarty Fitzpatrick Hogan Connolly"),
    'scottish': group(
        'Jessie Isabella Christina Janet Agnes Margaret Euphemia Marion Grace Helen Mary Elizabeth Ann Jane '
        'Catherine Elspeth Barbara Williamina Jemima Robina Georgina Jean Flora Annie Effie Rachel Sarah Bella '
        'Davina Jacobina Thomasina',
        'Alexander Duncan Hugh Angus Donald Archibald Malcolm Robert Andrew David John James William Thomas '
        'George Peter Colin Neil Kenneth Allan Ewan Lachlan Murdo Roderick Dugald Walter Gilbert Adam Charles '
        'Henry Daniel Ninian Hector Norman Gavin Matthew',
        '',
        'Macdonald Campbell Stewart Robertson Murray Fraser Grant Reid Cameron Ross Henderson Paterson '
        'Mackenzie Mackay Macleod Maclean Johnston Scott Anderson Smith Brown Thomson Wilson Kerr Hamilton '
        'Mitchell Watson Gordon Morrison Ferguson Sinclair Munro Douglas Cunningham Kennedy'),
    'jewish': group(
        'Rachel Leah Rebecca Esther Hannah Miriam Rosa Fanny Sophia Betsy Sarah Rose Kate Annie Dinah Judith '
        'Bella Golda Rivka Chaya Malka Feiga Deborah Rosetta Kitty Amelia Julia Matilda Phoebe Bertha Clara '
        'Minnie Lily',
        'Isaac Samuel Moses Solomon Abraham Joseph Lewis Nathan Benjamin Hyman David Jacob Aaron Mark Henry '
        'Israel Barnett Woolf Lazarus Morris Myer Simon Michael Emanuel Asher Phineas Mordecai Harris Louis '
        'Jonas Philip Alfred Reuben Joel Elias',
        '',
        'Cohen Levy Isaacs Jacobs Hart Moss Abrahams Myers Solomon Lazarus Goldsmith Mendoza Samuels Davis '
        'Harris Lyons Phillips Marks Joseph Nathan Levi Moses Benjamin Franks Barnett Rosenberg Goldstein '
        'Lipman Woolf Emanuel Henriques Schwartz Silverman Gompertz'),
    'italian': group(
        'Maria Giuseppina Rosa Teresa Angela Lucia Carmela Anna Caterina Francesca Margherita Luigia Antonia '
        'Giovanna Filomena Assunta Carolina Elisabetta Domenica Concetta Annunziata Raffaella Vincenza '
        'Michelina Angiolina Pasqualina Marianna Clementina Giulia Elena Clotilde Adelaide Agnese Luisa',
        'Giuseppe Antonio Giovanni Luigi Pietro Carlo Domenico Francesco Angelo Michele Vincenzo Pasquale '
        'Lorenzo Andrea Battista Giacomo Paolo Stefano Raffaele Alfonso Gaetano Salvatore Filippo Bartolomeo '
        'Enrico Achille Ercole Cesare Agostino Natale Emilio Federico Vittorio',
        '',
        'Ricci Bianchi Gatti Ferrari Costa Ortelli Gazzi Negretti Zambra Pagliai Rossi Romano Russo Lombardi '
        'Colombo Bertolini Mariani Conti Rinaldi Fontana Moretti Bruno Marino Galli Cavalli Grossi Brunetti '
        'Sartori Mancini Ronchetti Pagani Gianelli'),
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
        'Eleanor Mabel Margaret Hawise Amice Constance Adeliza Ela Lucy Eva Basilia Maud Gundreda Aline '
        'Clemence Nichola Idonea',
        'William Robert Richard Ralph Hugh Walter Geoffrey Roger Gilbert Henry Simon Thomas Nicholas Baldwin '
        'Reginald Guy Hamo Ranulf Eustace Fulk Alan Bertram Payn Roland Stephen Peter Philip Humphrey Miles '
        'Waleran Osbert',
        '',
        'de_Clare de_Lacy Mortimer Peverel Basset Beauchamp Mandeville Giffard Clifford Malet Ferrers Talbot '
        'de_Vere Bigod Percy Mowbray de_Warenne Fitzalan Courtenay Neville Despenser Grey de_Bohun Marshal '
        'de_Montfort Lovel Saint_John Bardolf Devereux Paynel'),
    'english': group(
        'Agnes Alice Maud Edith Joan Emma Margery Christina Godiva Elfrida Wymarc Ellen Annot Tibb Mariot '
        'Isabel Cecily Juliana Matilda Margaret Katherine Lettice Amice Avice Sibyl Mabel Hawise Denise Felicia '
        'Rose Lucy Beatrice Gunnild Idonea Eva',
        'John Thomas Adam Walter Wat Hob Robin Peter Simkin Edwin Godric Alfred Osric Wulfric Tom Dickon '
        'William Richard Robert Henry Roger Hugh Nicholas Ralph Geoffrey Gilbert Stephen Alan Simon Philip '
        'Laurence Jordan Elias Osbert Hamo Ranulf Gervase Martin',
        '',
        'Atwood Miller Smith Baker Fletcher Carter Thatcher Webster Brewer Cooper Turner Shepherd Fisher Wright '
        'Chapman Mason Ward Fowler Gardner Bowyer Cook Taylor Skinner Tanner Dyer Hunt Reeve Glover Webb Walker '
        'Spencer Palmer Fuller Barker Attwell Bywater Underwood'),
    'welsh': group(
        'Gwen Angharad Nest Gwenllian Morfudd Eluned Tangwystl Lleucu Efa Generys Gwladus Dyddgu Mallt Margred '
        'Annes Gwerful Myfanwy Gwenhwyfar Elen Senena Ales Hunydd Gwenfrewi Mabli Iwerydd Cristin Euron Jonet '
        'Lowri Catrin Elliw',
        'Dafydd Rhys Owain Gruffudd Madog Iorwerth Llywelyn Hywel Ieuan Einion Cadwgan Maredudd Cynan Tudur '
        'Goronwy Ithel Bleddyn Rhodri Cadwaladr Morgan Trahaearn Ednyfed Phylip Gwilym Llywarch Meurig Cynwrig '
        'Heilyn Cadell Rhirid Seisyll Caradog Elidir Iago Adda',
        '',
        'ap_Rhys ap_Owain ferch_Madog Gwyn Llwyd Vychan Goch Ddu ap_Dafydd ap_Gruffudd ap_Ieuan ap_Hywel '
        'ap_Madog ap_Llywelyn ap_Einion ap_Iorwerth ap_Maredudd ap_Tudur ap_Cynwrig ap_Goronwy ap_Ithel '
        'ferch_Dafydd ferch_Rhys ferch_Gruffudd ferch_Ieuan ferch_Hywel Moel Bach Hir Crach Gethin'),
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
        'Maria Josefa Refugio Guadalupe Dolores Manuela Juana Soledad Petra Ramona Trinidad Carmen Francisca '
        'Antonia Rosa Teresa Luz Paula Rafaela Concepcion Encarnacion Ignacia Jesusa Gertrudis Isabel Ana Rita '
        'Lugarda Mercedes Altagracia Marcelina Feliciana Leonor Victoria Margarita',
        'Jose Juan Manuel Francisco Jesus Ignacio Pedro Ramon Antonio Santiago Esteban Rafael Miguel Jose_Maria '
        'Luis Tomas Joaquin Felipe Andres Agustin Vicente Cristobal Julian Bernardo Teodoro Marcos Nicolas '
        'Mariano Lorenzo Gregorio Ysidro Tiburcio Atanacio Bartolo Anastasio Diego',
        '',
        'Romero Elias Ochoa Pacheco Ortiz Telles Leon Aguirre Robles Samaniego Contreras Salazar Montoya Garcia '
        'Martinez Lopez Sanchez Chavez Vigil Lucero Baca Sandoval Archuleta Valdez Gallegos Armijo Otero Luna '
        'Sena Trujillo Gonzales Duran Moreno Estrada Carrillo'),
    'cornish': group(
        'Jenefer Mary Elizabeth Grace Thomasine Loveday Jane Kitty Ann Mary_Ann Honour Philippa Wilmot Tamsin '
        'Patience Prudence Jenny Emily Eliza Catherine Susan Martha Charity Mercy Sarah Hannah Ellen Harriet '
        'Emma Bessie Annie Johanna',
        'John Richard William Nicholas Josiah Hart Jabez Thomas Samuel Edward James Henry Joseph George Peter '
        'Stephen Francis Matthew Philip Charles Simon Benjamin Joel Elisha Ezekiel Digory Hannibal Mark Michael '
        'Paul Abraham Jacob Silas Walter',
        '',
        'Trevithick Penrose Polglase Tregear Pascoe Trelawny Nankivell Rowe Bolitho Pengelly Tremayne Chenoweth '
        'Trevena Trethewey Tregonning Penhaligon Pendarves Jory Jago Hocking Hosking Williams Rule Nance Oates '
        'Tonkin Uren Rodda Curnow Trewartha Kitto Polkinghorne Spargo Dunstan'),
    'irish': group(
        'Bridget Mary Margaret Annie Kate Nora Ellen Catherine Johanna Honora Julia Ann Mary_Ann Elizabeth '
        'Delia Winifred Sarah Hannah Alice Teresa Agnes Rose Jane Eliza Maggie Lizzie Nellie Bessie Abbie Susan '
        'Josephine Celia',
        'Patrick Michael Dennis Timothy Cornelius Owen Daniel John James Thomas William Edward Bartholomew '
        'Jeremiah Terence Hugh Martin Peter Francis Joseph Bernard Matthew Laurence Andrew Charles Richard '
        'Maurice Myles Felix Edmund Thady Barney',
        '',
        "O'Rourke Sweeney Daly Hogan Mahoney Riordan Cassidy Moran Sullivan Murphy O'Brien Kelly Ryan Walsh "
        "Kennedy McCarthy Donovan Burke Fitzgerald Carroll Nolan Quinn Connolly Dwyer Kearney Duffy Lynch "
        "McGrath Shea Hennessy Brady Tobin"),
    'german': group(
        'Anna Katharina Margaretha Elisabeth Louisa Wilhelmina Emma Maria Christina Sophia Barbara Magdalena '
        'Dorothea Friederike Caroline Johanna Bertha Amalia Paulina Rosina Augusta Mathilde Theresa Clara Lina '
        'Minna Ida Helena Henriette Charlotte Frieda Eva',
        'Johann Friedrich Heinrich Wilhelm Karl August Otto Georg Jakob Philipp Peter Ludwig Christian Adam '
        'Konrad Michael Franz Joseph Hermann Gottlieb Ernst Gustav Martin Andreas Valentin Anton Fritz '
        'Christoph Nikolaus Matthias Adolph Rudolph',
        '',
        'Schmidt Becker Vogel Hartmann Kessler Lutz Brunner Weber Zimmermann Mueller Schneider Fischer Meyer '
        'Wagner Schulz Hoffmann Koch Bauer Richter Klein Wolf Schroeder Neumann Schwarz Braun Krueger Hofmann '
        'Lange Werner Krause Meier Lehmann'),
    'chinese': group(
        'Ah_Ying Mei_Lan Gum_Moy Sing_Toy Lai_Ho Ah_Toy Ah_Moy Ah_Kum Ah_Lan Ah_Yuk Ah_Hoy Ah_Choy Ah_Sue Ah_Ho '
        'Ah_Yoke Ah_Fah Ah_Ngan Ah_Kew Ah_Chun Ah_Lin Gum_Ying Kum_Ho Yut_Ho Yee_Toy Sing_Moy Lin_Moy Kum_Fong '
        'Lai_Ying Fung_Moy Choy_Lin Moy_Ying Yuen_Kum Sue_Kum',
        'Ah_Sam Wing Chung Fook Quong Hop_Kee Sing Ah_Sing Ah_Lee Ah_Kee Ah_Wing Ah_Fong Ah_Chung Ah_Hing '
        'Ah_Quong Ah_Yen Ah_Fook Ah_Louie Ah_Chew Ah_Gow Ah_Hop Ah_Jim Ah_Tom Hong Hing Kee Lung Chew Yuen Bing '
        'Gong Tong Fat Quan Yick',
        '',
        'Lee Wong Chan Chin Yee Ng Fong Louie Moy Lum Fung Quan Leong Gin Tom Jue Dea Toy Hom Woo Eng Yuen Hong '
        'Lau Mah Poon Chew Dong Joe Gee Kwong Jung'),
}

STORYBOOK = {
    'plain': group(
        'Hester Marigold Tansy Prudence Wilhelmina Bettony Dulcie Maud Bess Ottilie Hazel Posy Clemency Ada '
        'Bryony Winnie Lettice Nell Tibby Gwendolyn',
        'Tobin Bram Hob Wendel Barnaby Ambrose Jory Ned Ferris Osgood Pip Cuthbert Dunstan Rollo Jasper Ezekiel '
        'Lem Horace Bartholomew Wilbur',
        'Robin Kit Jem Frankie',
        'Thistlewood Puddifoot Hobbs Mossley Applegarth Wickham Fennimore Crumb Featherstone Tillbrook Underhay '
        'Oakshott Fairweather Cotton Tanner Pickering Dimmock Hobday Gammage Ottley Brewster Cobb Pennington Ashby '
        'Goodbody Littlejohn Shepherd Weaver Hatcher Merriman'),
}

EDO_JAPAN = {
    'townsfolk': group(
        'Ume Kiku Matsu Take Haru Tsuru Kame Sen Toku Fuku Kin Gin Tome Sato Yoshi Tami Ito Masa Tsune Nobu '
        'Hisa Kiyo Shige Fusa Mitsu Toyo Naka Rin Sayo Chiyo Yasu Mine Kane',
        'Kichibei Jinbei Rokubei Chobei Kyubei Sobei Zenbei Mohei Kihei Gohei Jiroemon Tasuke Yasubei Kahei '
        'Kichizo Shinsuke Tokubei Ihei Seijiro Manzo Shinzo Tomekichi Kichiemon Gosuke Denbei Sakichi Genshichi '
        'Heisuke Yohei Chojiro Ichibei Kyuzo Hachibei Seibei',
        '',
        'Echigoya Mitsui Omiya Iseya Daikokuya Kinokuniya Masuya Yamatoya Kagiya Tsutaya Shirokiya Daimaruya '
        'Matsuzakaya Konoike Izumiya Fujiya Edoya Kazusaya Owariya Mikawaya Tokiwaya Ebisuya Kikuya Sakaiya '
        'Naraya Tamaya Yorozuya Echizenya Surugaya Tachibanaya Yamazakiya Nagasakiya'),
    'samurai': group(
        'Tsuru Kayo Ei Kiku Nui Sachi Iyo Teru Fusa Masa Toshi Yuki Sano Hide Sumi Michi Ritsu Sono Waka Tama '
        'Chika Nao Yoshi Shizu Mine Iso Tomo Sen Kazu Fumi Matsu Taka',
        'Kurando Hayato Gunji Denzaemon Kyuzaemon Kazuma Heima Hyogo Tatewaki Gonnosuke Sakon Ukon Jubei Kanbei '
        'Matabei Hikoemon Shozaemon Tadataka Masanobu Yoshinobu Tadashige Shigemasa Kiyomasa Masayuki Yoshitaka '
        'Naoyuki Tomonori Sadanobu Tadakuni Gennai Sanai Heihachiro Kuranosuke Chuzaemon',
        '',
        'Matsudaira Honda Sakai Okubo Ishikawa Sakakibara Naito Abe Mizuno Ogasawara Hosokawa Kuroda Asano '
        'Nabeshima Shimazu Mori Yamauchi Todo Hachisuka Uesugi Satake Tsugaru Hotta Inaba Doi Toda Ando Itakura '
        'Okudaira Oishi Saigo Yoshida Katsu Watanabe'),
    'farming': group(
        'Ume Take Matsu Tora Kuma Iku Tatsu Sute Natsu Aki Kayo Shina Tome Kame Haru Yae Fuji Nami Sada Toki '
        'Kuni Mitsu Iwa Tsuta Hana Tsuya Miyo Sue Hatsu Kiyo Ine Riku',
        'Gonbei Sakubei Tasaku Mosuke Yosaku Kyusaku Jinsaku Hachiro Genzo Magoemon Gorobei Matazo Jinzaemon '
        'Kichiji Tomezo Kumazo Torakichi Sankichi Yoshizo Kanzo Heizo Isaku Sakuzo Tokuzo Matsuzo Kamekichi '
        'Ushimatsu Uemon Yazaemon Gonzo Denzo Shichibei',
        '',
        'Kamimura Shimomura Nakamura Kitamura Nishimura Tanaka Yamashita Ishida Hara Ota Ikeda Hayashi '
        'Kawaguchi Hirano Inoue Matsumoto Takeuchi Sakamoto Ogawa Fujita Kawai Ono Uchida Murakami Noguchi '
        'Sugiyama Tsuchiya Yokoyama Okada Iwasaki'),
}

QING_CHINA = {
    'han': group(
        'Guiying Xiulan Yulan Shuzhen Guizhen Yuzhen Xiuzhen Fengying Cuiying Jinlan Yulian Guilan Suzhen '
        'Lanying Qiaoyun Cuilan Aizhen Shuying Huilan Baozhu Jinfeng Caifeng Yufeng Meilan Lianying Xiuying '
        'Hehua Qiuxiang Chunmei Shuyun Jinying Guifang Yinzhu Xiaomei',
        'Dehai Fugui Changgeng Yongfu Shunfa Rongbao Tianci Jinbao Qingyun Dexing Fuquan Yongqing Jinsheng '
        'Baoshan Changshun Laifu Wanfu Shoushan Zhaolin Hongen Tingyu Jishan Mingde Zhenbang Shoulin Guozhen '
        'Hanzhang Liansheng Fuhai Zengxiang Wenbin Guoliang',
        '',
        'Wang Li Zhang Liu Chen Yang Zhao Huang Zhou Wu Xu Sun Hu Zhu Gao Lin He Guo Ma Luo Liang Song Zheng '
        'Xie Han Tang Feng Yu Dong Xiao Cao Cheng'),
    'manchu': group(
        'Shuxian Yurong Wanrong Huifen Shuhua Yuxiu Jingfang Shufang Ruiyun Guixiang Rongfen Defang Jingyi '
        'Yuqing Shulan Rongzhen Yinghua Fengxian Lanxiang Xiuyun Cuifeng Guiqin Shuqin Yuqin Jingzhen Daniu '
        'Erniu Sanniu Siniu Xiaoniu Fuxiang Ruifen',
        'Ronglu Wenxiang Baojun Gangyi Duanfang Ruilin Linggui Chongqi Chonghou Shengyu Yulu Kuijun Jingshan '
        'Yinchang Tieliang Xiliang Lianyuan Chongli Guangshou Yuqian Qishan Ruichang Jinliang Enming Duolonga '
        'Mingliang Shengbao Delenggetai Huaitapu Zhirui Wenqing Mukedengbu',
        '',
        'Aisin_Gioro Gioro Gualgiya Niohuru Tunggiya Heseri Fuca Yehe_Nara Ula_Nara Hada_Nara Hoifa_Nara Nara '
        'Magiya Irgen_Gioro Sirin_Gioro Donggo Janggiya Uya Sakda Bayara Tatara Socoro Ligiya Hitara Sumuru '
        'Ujala Gorolo Wanggiya Guan Tong Fu'),
    'hakka': group(
        'Xiumei Jiaomei Lanmei Yumei Fengmei Jinmei Chunmei Qiumei Dongmei Guimei Ermei Sanmei Simei Taomei '
        'Lianmei Xuanjiao Lianying Yingniang Jinniang Yuniang Fengniang Xiuniang Lanniang Cuiniang Meiniang '
        'Yuzhen Shuying Jiaoying Guiying Ahfeng Siying Jinhua',
        'Xiuquan Rengan Yunshan Xiuqing Chaogui Dakai Rengda Renfa Fengxiang Jinfa Renlong Tianfu Guangyao '
        'Wenhai Yongfa Zhongliang Dingguo Rongguang Sihai Mingqing Huanzhang Jiaxiang Fuchang Delin Shaoxiang '
        'Zhaohe Ahfu Agui Ashun Asheng Along Ahai',
        '',
        'Chen Li Huang Zhang Liu Lin Zeng Wu Luo Xie Ye Zhong Peng Qiu Liao Yang He Xu Jiang Lai Fan Hong Wen '
        'Tang Gu Wei Hou Yu Zhuo Tu Feng'),
}

OTTOMAN = {
    'turkish': group(
        'Ayse Fatma Emine Hatice Zeynep Hafize Saliha Nefise Rukiye Hayriye Nazife Sadiye Saide Hamide Habibe '
        'Esma Sakine Meryem Zehra Naile Halime Fitnat Gulsum Nazli Mihri Pakize Nadide Cemile Feride Behiye '
        'Refika Atiye Safiye Huriye',
        'Mehmed Ahmed Ali Mustafa Hasan Huseyin Ibrahim Ismail Osman Suleyman Halil Yusuf Abdullah Hakki Hilmi '
        'Rifat Sadik Tevfik Kamil Emin Salih Riza Nuri Halim Fehmi Edhem Ragip Necib Sevket Fuad Zeki Arif Omer '
        'Bekir',
        '',
        'Ahmedoglu Kasapzade Hoca Hacioglu Mehmedoglu Hasanoglu Osmanoglu Alioglu Mustafaoglu Ibrahimoglu '
        'Kalaycioglu Demircioglu Karaosmanoglu Cerrahzade Imamzade Hafizzade Kadizade Mollazade Bakkal Berber '
        'Terzi Kunduraci Haci Arnavut Topal Deli Kara Uzun Sarioglu Bostanci Hamal Kaptan'),
    'greek': group(
        'Maria Eleni Aikaterini Sofia Anna Despina Kalliopi Evanthia Theodora Vasiliki Eirini Zoe Chrysoula '
        'Angeliki Alexandra Smaragda Efrosyni Paraskevi Kyriaki Marigo Evdokia Anastasia Ioanna Georgia '
        'Polyxeni Fotini Stamatia Argyro Penelope Euterpe Chrysanthi',
        'Georgios Ioannis Konstantinos Dimitrios Nikolaos Vasileios Panagiotis Christos Athanasios Antonios '
        'Stylianos Michail Alexandros Emmanouil Theodoros Stavros Pavlos Petros Spyridon Evangelos Charalambos '
        'Apostolos Leonidas Grigorios Andreas Stefanos Kyriakos Anastasios Prodromos Ilias Aristeidis Zacharias',
        '',
        'Papadopoulos Karatzas Mavrokordatos Zografos Vlastos Zarifis Georgiadis Ioannidis Konstantinidis '
        'Nikolaidis Dimitriadis Hatziioannou Oikonomou Theodoridis Christodoulou Sideridis Pappas Vafiadis '
        'Eugenidis Stavridis Kalfas Antoniadis Pavlidis Michailidis Hatzopoulos Vasileiou Raftopoulos Mavros '
        'Siniossoglou Baltazzi Skouloudis'),
    'armenian': group(
        'Mariam Anna Takuhi Zabel Srpuhi Hripsime Arshaluys Nvart Siranush Haiganush Satenik Lusin Gayane '
        'Anahid Hermine Elmas Mari Aznive Vartanush Shushan Zaruhi Araksi Hranush Nazeli Makruhi Yeranuhi '
        'Varsenik Ovsanna Sirarpi Agavni Diruhi Marta',
        'Hagop Garabed Krikor Boghos Bedros Hovhannes Mardiros Ohannes Sarkis Kevork Haroutioun Mihran Nishan '
        'Avedis Arshag Dikran Vahan Levon Aram Nerses Mesrob Zareh Setrak Simon Kaloust Vartan Khachadur Diran '
        'Hrant Onnik Minas Hovsep',
        '',
        'Gulbenkian Dadian Balyan Duzian Bezjian Kazazian Hagopian Garabedian Krikorian Boghosian Bedrosian '
        'Ohanian Sarkisian Kevorkian Haroutiounian Mardirosian Nishanian Avedisian Tashjian Kouyoumjian '
        'Demirjian Yazejian Terzian Bakalian Kalfayan Papazian Topalian Hovsepian Abajian Simonian Odian '
        'Kalebjian'),
    'sephardic': group(
        'Rahel Reina Sol Luna Estrea Bulisa Djoya Vida Allegra Sara Ester Rivka Lea Miryam Klara Rosa Buena '
        'Fortuna Oro Perla Sultana Benvenida Gracia Mazal Palomba Rebeka Djamila Flor Signora Merkada Simha '
        'Dudu',
        'Avram Isak Yakov Moshe Yosef Shemuel Shabetay Haim Bohor Nissim Eliau Yehuda Menahem Salomon Mordehai '
        'Rafael Daniel Aron David Bension Mair Yom_Tov Zaharia Jako Leon Vitali Gavriel Pinhas Hezkia Albert '
        'Ezra Marko',
        '',
        'Behar Levi Kohen Alhadeff Abravanel Benveniste Camondo Carasso Franco Gabay Hasson Halfon Eskenazi '
        'Farhi Mizrahi Navarro Toledano Saporta Amado Algranti Baruh Bensussan Kamhi Pardo Policar Russo '
        'Taragan Uziel Varon Danon Ventura Arditi Mitrani Mallah'),
}

ANCIENT_ROME = {
    'roman': group(
        'Julia Cornelia Claudia Antonia Valeria Caecilia Flavia Domitia Sulpicia Pompeia Fabia Aemilia Junia '
        'Livia Octavia Calpurnia Licinia Plotina Annia Vibia Statilia Servilia Marcia Tullia Porcia Agrippina '
        'Faustina Sabina Plautia Ulpia Paulina Pomponia Sempronia Terentia Lucilla',
        'Gaius Lucius Marcus Publius Quintus Titus Tiberius Gnaeus Aulus Sextus Decimus Servius Spurius Manius '
        'Appius Numerius Mamercus Vibius Rufus Secundus Maximus Severus Priscus Gallus Celer Crispus Sabinus '
        'Fuscus Paullus Proculus Clemens Firmus',
        '',
        'Julius Cornelius Claudius Valerius Caecilius Flavius Domitius Sulpicius Pompeius Fabius Aemilius '
        'Junius Livius Octavius Calpurnius Licinius Annius Vibius Statilius Servilius Marcius Tullius Porcius '
        'Plautius Ulpius Antonius Sempronius Cassius Fulvius Terentius Petronius Pomponius'),
    'greek': group(
        'Chloe Tyche Helpis Phoebe Daphne Irene Eutychia Agathe Chrysis Eutyche Nymphe Syntyche Tryphaena '
        'Tryphosa Euhodia Lydia Persis Doris Zosime Callityche Erotis Thais Philumena Glycera Nice Moschis '
        'Charis Hermione Antiochis Stephanis Euphrosyne Hedone',
        'Hermes Eros Philemon Onesimus Epaphroditus Narcissus Pallas Diogenes Eutychus Trophimus Hermas '
        'Philetus Alexander Dionysius Apollonius Zosimus Antiochus Heraclides Aristobulus Chrysippus Callistus '
        'Epictetus Philologus Isidorus Sosthenes Stephanus Theophilus Tychicus Agathocles Demetrius Menander '
        'Herodion Asclepiades',
        '',
        'Julius Claudius Flavius Ulpius Cocceius Domitius Antonius Valerius Cornelius Aemilius Caecilius '
        'Licinius Pompeius Sempronius Terentius Statilius Vettius Lollius Mussius Naevius Publicius Sallustius '
        'Marcius Annaeus Seius Herennius Plotius Tullius Volusius Calpurnius'),
    'provincial': group(
        'Prima Secunda Tertia Quarta Maxima Severa Saturnina Januaria Fortunata Victorina Honorata Donata '
        'Felicula Rogata Urbica Verecunda Regina Namgedde Successa Ingenua Materna Candida Optata Quieta '
        'Restituta Crescentia Rustica Lepidina Victoria Primitiva Felicitas Perpetua',
        'Saturninus Rogatus Donatus Fortunatus Felix Victor Januarius Honoratus Vitalis Secundus Tertius Primus '
        'Crescens Faustus Ingenuus Datus Optatus Successus Verecundus Senecio Cintusmus Bellicus Catavignus '
        'Vepogenus Brigomaglos Tasciovanus Hanno Himilco Mago Namphamo Restitutus Rusticus',
        '',
        'Julius Claudius Flavius Ulpius Cocceius Pompeius Valerius Antonius Cornelius Caecilius Fabius Junius '
        'Licinius Aemilius Sempronius Maternius Secundinius Victorius Primius Justinius Sentius Sulpicius '
        'Marius Vibius Gargilius Sittius Egnatius Helvius Atilius Arruntius'),
}

MUGHAL_INDIA = {
    'muslim': group(
        'Fatima Zainab Ayesha Khadija Maryam Amina Halima Sakina Rabia Zubaida Hamida Salima Rahima Karima '
        'Jamila Hasina Gulnar Shirin Zahra Habiba Latifa Najma Sultana Bilqis Ruqaiya Mahbuba Asma Saliha '
        'Dilaram Mehrunnisa Gulbadan Sharifa',
        'Muhammad Ahmad Ali Hasan Husain Abdullah Abdul_Karim Abdul_Rahim Ismail Ibrahim Yusuf Daud Sulaiman '
        'Qasim Jafar Mahmud Farid Nur_Muhammad Sher Khizr Mansur Rahmat Hafiz Karim Latif Salim Murad Bahadur '
        'Fazl Inayat Rustam Hamid Nasir',
        '',
        'Khan Shaikh Sayyid Mirza Beg Ansari Siddiqui Qureshi Lodi Barlas Chughtai Bukhari Naqvi Rizvi Hashmi '
        'Farooqi Usmani Gilani Qadiri Chishti Badakhshi Husaini Bilgrami Tirmizi Kirmani Shirazi Isfahani '
        'Mashhadi Kashmiri Abbasi Yusufzai'),
    'hindu': group(
        'Sita Radha Lakshmi Parvati Ganga Yamuna Kamala Savitri Durga Gauri Saraswati Tulsi Rukmini Champa '
        'Chameli Malati Kausalya Anandi Bhagwati Devaki Godavari Janki Kesar Kunti Padma Sundari Uma Lilavati '
        'Mohini Hira Phulmati Annapurna',
        'Ram Krishna Gopal Govind Hari Mohan Shyam Balram Kishan Narayan Raghunath Tukaram Keshav Madhav '
        'Ram_Das Mathura_Das Jagannath Gangadhar Damodar Shankar Mahadev Ganesh Lalchand Sundar Dayaram Gokul '
        'Banarasi Bhagwan_Das Hiranand Sitaram Virji Shantidas',
        '',
        'Mishra Tiwari Pandey Dubey Shukla Chaturvedi Trivedi Joshi Bhatt Dikshit Upadhyay Agarwal Khatri Mehta '
        'Shah Seth Verma Saxena Mathur Srivastava Nagar Desai Patil Deshmukh Kulkarni Pandit Chaudhuri Mazumdar '
        'Basu Ghosh Mitra Datta Sen Vora Jhaveri'),
    'rajput': group(
        'Padmavati Karnavati Jaivanta Mira Hansa Tara Sajjan_Kanwar Chand_Kanwar Ratan_Kanwar Gulab_Kanwar '
        'Sugan_Kanwar Kishan_Kanwar Indra_Kanwar Roop_Kanwar Anand_Kanwar Bhanwar_Kanwar Champa_Kanwar '
        'Phool_Kanwar Kesar_Kanwar Suraj_Kanwar Dhan_Kanwar Man_Bai Hira_Bai Lakshmi_Bai Rupa_Bai Sona_Bai '
        'Ajab_Kanwar Jas_Kanwar Ganga_Bai Padma_Kanwar Shyam_Kanwar Umade',
        'Pratap Amar Karan Jagat Man Jaswant Gaj Ajit Bhim Ratan Sur Jai Bishan Chandrasen Maldeo Jaimal Patta '
        'Raghunath Kesri Hammir Anand Prithviraj Kalyan Kumbha Sangram Sujan Indra Bhupat Udai Mukund Durgadas '
        'Bhagwant',
        '',
        'Singh Rathore Sisodia Kachhwaha Chauhan Hada Bhati Parmar Solanki Tomar Jhala Gaur Chandel Bundela '
        'Baghela Guhilot Shekhawat Champawat Jadeja Deora Sengar Bais Raghuvanshi Bhadoria Gaharwar Katoch '
        'Pundir Bargujar Khichi Songara Kumpawat Jodha'),
}

# Victorian and frontier people take given names popular in their birth year too (era_years in
# given_names.py sets the year the story is told), but keep the period family names above.
PERIOD_CULTURES = {
    'victorian': (VICTORIAN, {'english': 'england-wales', 'west-riding': 'england-wales', 'irish': 'ireland',
                              'scottish': 'scotland', 'jewish': 'jewish-diaspora', 'italian': 'italy'}),
    'frontier': (FRONTIER, {'american': 'us', 'mexican': 'mexico', 'cornish': 'england-wales', 'irish': 'ireland',
                            'german': 'germany'}),
}
for bank, links in PERIOD_CULTURES.values():
    for key, culture in links.items():
        bank[key] |= {'cultures': {culture: 1}, 'own_family': True}

BANKS = {'modern': MODERN, 'victorian': VICTORIAN, 'medieval': MEDIEVAL, 'frontier': FRONTIER, 'storybook': STORYBOOK,
         'edo-japan': EDO_JAPAN, 'qing-china': QING_CHINA, 'ottoman': OTTOMAN, 'ancient-rome': ANCIENT_ROME,
         'mughal-india': MUGHAL_INDIA}

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
        # A city in 2077, mixed from the whole world rather than one country.
        'future': {'bank': 'modern', 'mix': {'anglo': 2, 'hispanic': 2.5, 'east-asian': 2.5, 'south-asian': 2,
                                             'black-american': 1.5, 'west-african': 1.5, 'arabic': 1, 'slavic': 0.8,
                                             'caribbean': 0.5, 'italian': 0.4, 'irish': 0.4, 'jewish': 0.3}},
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
