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
        'Lucy Rose Kate Beatrice Agnes Lilian Violet Mabel Ethel Ann Margaret Eliza Charlotte Frances Fanny '
        'Caroline Catherine Susan Hannah Jessie Lily Amy Nellie Gertrude Maud Dorothy Minnie Elsie Lizzie '
        'Bertha Eleanor Isabella Amelia Julia Sophia Matilda Esther Rebecca Phoebe Rachel Ruth Maria Georgina '
        'Henrietta Adelaide Victoria Evelyn Gladys Hilda Ivy May Daisy Grace Kathleen Winifred Mildred Marion '
        'Laura Helen Lydia Selina Rosina Rosa Charity Emmeline Eva Ida Lottie Sophie Hester Leah Miriam Anne '
        'Jemima Keziah Dinah Bessie Polly Sally Betsy Nancy Rhoda Constance Olive',
        'William John George Thomas James Charles Henry Frederick Arthur Albert Alfred Walter Joseph Edward '
        'Robert Samuel Ernest Herbert Harry Richard Francis Percy Sidney Frank Edwin David Daniel Benjamin '
        'Isaac Edmund Edgar Harold Leonard Stanley Reginald Horace Hugh Matthew Peter Philip Stephen Michael '
        'Andrew Christopher Ralph Lewis Cecil Bertram Clement Cyril Claude Douglas Gilbert Howard Jacob Jesse '
        'Jonathan Joshua Lionel Louis Martin Maurice Nathaniel Oliver Oswald Owen Reuben Roland Rupert Tom '
        'Victor Wilfred Willie Abraham Amos Aaron Adam Alexander Ambrose Archibald Arnold Austin Basil Bernard '
        'Charlie Clarence Elijah Enoch Ezra Felix Gabriel Gerald Gordon Hubert Humphrey Jabez Jack Josiah '
        'Laurence Levi',
        '',
        'Smith Jones Williams Taylor Brown Davies Wilson Evans Thomas Johnson Roberts Robinson Wright Wood Hall '
        'Green Walker Hughes Edwards Lewis Turner Jackson Harris Clarke Cooper Ward Morris King Baker Harrison '
        'Allen Mitchell Hill Parker Price Bennett Cox Fletcher Pearce Webb Holloway Marsh Pritchard Thompson '
        'White Martin Moore Clark Young Scott Morgan Cook Phillips Shaw Lloyd Carter Collins Bell Murphy '
        'Richardson Marshall Simpson Ellis Adams Chapman Mason Rogers Stevens Hunt Butler Barnes Fisher Knight '
        'Harvey Russell Pearson Graham Gibson Kelly Dixon Hayes Wells Holmes Matthews Fox Grant Lawrence Mills '
        'Palmer Payne Saunders Spencer Stone Hunter Hart Andrews Atkinson Bailey Barker Bird'),
    'irish': group(
        'Bridget Catherine Margaret Honora Ellen Mary Johanna Nora Kate Julia Anne Winifred Eliza Sarah '
        'Elizabeth Annie Teresa Agnes Alice Delia Sabina Abina Kitty Hannah Jane Rose Josephine Maggie Lizzie '
        'Bessie Christina Susan Ann Mary_Ann Peggy Molly Nellie Katie Minnie Ellie Jenny Nancy Sally Biddy '
        'Kathleen Frances Fanny Isabella Sophia Martha Maria Cecilia Celia Monica Anastasia Deborah Penelope '
        'Una Grace Helena Helen Esther Emily Louisa Margery Barbara Lucy Letitia Philomena Bernadette Agatha '
        'Rosanna Eleanor Mabel Amelia Charlotte Harriet Caroline Matilda Judith Joanna Emma Laura Lena Jessie '
        'Eveline Edith Alicia Marcella Debby Polly Betty Elsie Florence Dorothy Rebecca Clara Gertrude Eileen '
        'Norah',
        'Patrick Michael John Daniel Timothy Cornelius Dennis Thomas Jeremiah Owen James William Edward '
        'Bartholomew Florence Terence Hugh Martin Peter Francis Joseph Bernard Matthew Laurence Christopher '
        'Andrew Charles Edmund Richard Maurice Thady Myles Felix Eugene Denis Darby Dermot Jerome Garrett '
        'Gerald Henry Luke Mark Morgan Nicholas Philip Robert Roger Stephen Simon Malachy Murtagh Neil Mortimer '
        'Anthony Ambrose Alexander Arthur George Paul Pierce Redmond Raymond Ulick Brian Manus Barney Dominick '
        'Colman Godfrey Oliver Samuel Sylvester Theobald Valentine Vincent Walter Randal Albert Alfred Austin '
        'Benjamin Frederick Louis Lewis Ellis David Jasper Roderick Matthias Malachi Constantine Moses Harry '
        'Frank Ned Mick Dan Tim Jerry',
        '',
        "Sullivan Murphy O'Brien Kelly Driscoll Connell Mahony Callaghan Doyle Byrne Flynn Brennan Ryan Walsh "
        "O'Neill Kennedy McCarthy Donovan Leary Regan Kavanagh Fitzgerald Burke Hayes Carroll Nolan Keane Quinn "
        "Daly Healy Kearney Moriarty Fitzpatrick Hogan Connolly Collins O'Connor Lynch Murray Dunne Brady Power "
        "Dempsey Farrell Gallagher Doherty Boyle Maguire McLoughlin Kane Devlin Kenny Reilly Clarke Keogh "
        "Whelan Foley Hurley Mullins O'Donnell Rooney McDonnell Flanagan Duggan Hickey Coleman Cullen Barry "
        "Ahern Barrett Butler Costello Cronin Crowley Cummins Curran Delaney Dillon Dolan Donnelly Doran Duffy "
        "Egan Fahy Finnegan Gleeson Griffin Hanlon Hennessy Higgins Horgan Keating Lawlor Lennon Lyons "
        "McCormack McGrath McKenna McMahon Madden"),
    'scottish': group(
        'Jessie Isabella Christina Janet Agnes Margaret Euphemia Marion Grace Helen Mary Elizabeth Ann Jane '
        'Catherine Elspeth Barbara Williamina Jemima Robina Georgina Jean Flora Annie Effie Rachel Sarah Bella '
        'Davina Jacobina Thomasina Marjory Christian Betty Peggy Kirsty Lilias Alison Henrietta Wilhelmina '
        'Johanna Nancy Katherine Ellen Eliza Joan Annabella Clementina Murdina Dolina Donalda Hughina Kate '
        'Morag Mairi Maggie Lizzie Nellie Minnie Ina Sophia Joanna Martha Susan Mina Lucy Louisa Charlotte '
        'Caroline Julia Frances Matilda Emily Alice Eleanor Harriet Hannah Esther Ishbel Rhoda Lily Mabel '
        'Violet Edith Ada Emma Florence Alexandrina Mary_Ann Katie Elsie Maud Ethel Rose Nora Beatrice Muriel '
        'Lilian Dora Amelia',
        'Alexander Duncan Hugh Angus Donald Archibald Malcolm Robert Andrew David John James William Thomas '
        'George Peter Colin Neil Kenneth Allan Ewan Lachlan Murdo Roderick Dugald Walter Gilbert Adam Charles '
        'Henry Daniel Ninian Hector Norman Gavin Matthew Fergus Farquhar Finlay Ronald Ranald Torquil Alister '
        'Calum Aeneas Sandy Magnus Mungo Quintin Innes Joseph Samuel Richard Edward Francis Frederick Arthur '
        'Albert Alfred Harry Ernest Herbert Patrick Michael Stephen Benjamin Isaac Jonathan Nathaniel Ebenezer '
        'Gideon Lewis Laurence Edwin Sidney Percy Douglas Leslie Graham Gordon Martin Philip Jacob Moses Ralph '
        'Simon Dougal Ivor Ian Hamish Alastair Somerled Gregor Bruce Crawford Murdoch Evan Willie Tom Archie',
        '',
        'Macdonald Campbell Stewart Robertson Murray Fraser Grant Reid Cameron Ross Henderson Paterson '
        'Mackenzie Mackay Macleod Maclean Johnston Scott Anderson Smith Brown Thomson Wilson Kerr Hamilton '
        'Mitchell Watson Gordon Morrison Ferguson Sinclair Munro Douglas Cunningham Kennedy Macgregor '
        'Mackintosh Maclachlan Macpherson Macmillan Macintyre Mackinnon Macrae Macaulay Macfarlane Macneil '
        'Macnab Mackie Macdougall Black White Young Miller Clark Taylor Martin Walker Wallace Bell Duncan Craig '
        'Allan Lindsay Graham Russell Hunter Shaw Ritchie Simpson Watt Boyd Logan Hay Burns Crawford Dunbar '
        'Lamont Laing Baird Bruce Buchanan Chisholm Drummond Erskine Forbes Gillespie Gunn Innes Keith Leslie '
        'Lockhart Maxwell Moffat Napier Ogilvie Rankin Rae Rutherford Sutherland Wylie'),
    'jewish': group(
        'Rachel Leah Rebecca Esther Hannah Miriam Rosa Fanny Sophia Betsy Sarah Rose Kate Annie Dinah Judith '
        'Bella Golda Rivka Chaya Malka Feiga Deborah Rosetta Kitty Amelia Julia Matilda Phoebe Bertha Clara '
        'Minnie Lily Gertrude Rosalie Augusta Caroline Charlotte Celia Dora Eva Emma Flora Florence Frances '
        'Henrietta Ida Isabella Jane Jessie Lena Louisa Lydia Maria Marian Martha Millie Paulina Polly '
        'Priscilla Rosalind Ruth Sadie Selina Susannah Theresa Zillah Ada Abigail Adelaide Alice Elizabeth '
        'Ellen Emily Freda Gussie Rosie Etta Yetta Zelda Sheindel Perel Pessie Gittel Hinda Mindel Bryna Shifra '
        'Sima Fruma Raizel Basha Bluma Breina Ettie Becky Simmy Zipporah Sophie Naomi',
        'Isaac Samuel Moses Solomon Abraham Joseph Lewis Nathan Benjamin Hyman David Jacob Aaron Mark Henry '
        'Israel Barnett Woolf Lazarus Morris Myer Simon Michael Emanuel Asher Phineas Mordecai Harris Louis '
        'Jonas Philip Alfred Reuben Joel Elias Daniel Edward Ephraim Ezekiel Frederick George Gabriel Isidore '
        'Jonathan Joshua Judah Julius Leon Leopold Levi Lionel Marcus Maurice Max Nathaniel Noah Raphael Samson '
        'Saul Sidney Victor Zachariah Albert Alexander Arthur Bernard Charles Ernest Harry Herbert Lawrence '
        'Leonard Montague Percy Ralph Edgar Augustus Ellis Elkan Gershon Hillel Jonah Kalman Lipman Naphtali '
        'Tobias Eleazar Gideon Chaim Mendel Hirsch Leib Selig Fishel Zalman Herschel Nachman Shmuel Barnet '
        'Sampson',
        '',
        'Cohen Levy Isaacs Jacobs Hart Moss Abrahams Myers Solomon Lazarus Goldsmith Mendoza Samuels Davis '
        'Harris Lyons Phillips Marks Joseph Nathan Levi Moses Benjamin Franks Barnett Rosenberg Goldstein '
        'Lipman Woolf Emanuel Henriques Schwartz Silverman Gompertz Aarons Adler Alexander Baron Bernstein '
        'Montefiore Mocatta Sassoon Belisario Lindo Lopes Nunes Pinto Sebag Rothschild Goldsmid Salomons '
        'Montagu Samuel Franklin Waley Elias Feldman Frankel Freedman Friedman Gold Goldberg Goldman Greenberg '
        'Gross Hyams Isaacson Israel Jacobson Josephs Kaplan Katz Klein Landau Levene Levin Levine Levinson '
        'Lewin Michaels Mendelsohn Oppenheim Polak Rosen Rosenthal Rubinstein Sachs Salaman Simmons Simons '
        'Stern Wolff Wolfson Zangwill Gluckstein Salmon Gollancz Hirsch Asher Davids'),
    'italian': group(
        'Maria Giuseppina Rosa Teresa Angela Lucia Carmela Anna Caterina Francesca Margherita Luigia Antonia '
        'Giovanna Filomena Assunta Carolina Elisabetta Domenica Concetta Annunziata Raffaella Vincenza '
        'Michelina Angiolina Pasqualina Marianna Clementina Giulia Elena Clotilde Adelaide Agnese Luisa '
        'Angelina Maddalena Rosina Rosaria Rachele Nicoletta Benedetta Lucrezia Cristina Laura Paola Gaetana '
        'Grazia Immacolata Marta Natalina Orsola Palmira Pasqua Santa Serafina Stella Virginia Vittoria Amalia '
        'Adele Albina Beatrice Bianca Camilla Candida Cecilia Celeste Chiara Costanza Emilia Erminia Eugenia '
        'Fortunata Gemma Gilda Giacinta Ida Ines Irene Isabella Italia Letizia Lina Livia Marcella Matilde '
        'Olimpia Ottavia Pia Pierina Regina Rita Rosalia Santina Silvia Sofia Ersilia Giuditta Ester Elvira',
        'Giuseppe Antonio Giovanni Luigi Pietro Carlo Domenico Francesco Angelo Michele Vincenzo Pasquale '
        'Lorenzo Andrea Battista Giacomo Paolo Stefano Raffaele Alfonso Gaetano Salvatore Filippo Bartolomeo '
        'Enrico Achille Ercole Cesare Agostino Natale Emilio Federico Vittorio Alessandro Anselmo Arturo '
        'Augusto Benedetto Bernardo Biagio Carmine Cristoforo Davide Ernesto Ettore Eugenio Felice Ferdinando '
        'Fortunato Gabriele Gennaro Gerardo Giacinto Gioacchino Giulio Guglielmo Ignazio Leonardo Leopoldo '
        'Lodovico Luciano Marco Mario Martino Matteo Nicola Ottavio Pellegrino Primo Riccardo Roberto Rocco '
        'Romolo Sebastiano Secondo Silvio Simone Tommaso Ugo Umberto Valentino Vito Alberto Amedeo Attilio '
        'Bruno Celestino Cosimo Costantino Edoardo Egidio Emanuele Faustino Fedele Giorgio Girolamo Giuliano '
        'Guido Isidoro Lazzaro',
        '',
        'Ricci Bianchi Gatti Ferrari Costa Ortelli Gazzi Negretti Zambra Pagliai Rossi Romano Russo Lombardi '
        'Colombo Bertolini Mariani Conti Rinaldi Fontana Moretti Bruno Marino Galli Cavalli Grossi Brunetti '
        'Sartori Mancini Ronchetti Pagani Gianelli Esposito Greco De_Luca Giordano Rizzo Lombardo Barbieri '
        'Fabbri Ferrara Caruso Leone Longo Gentile Martinelli Vitale Serra De_Santis Marchetti Parisi Villa '
        'Conte Ferri Fiore Testa Pellegrini Palumbo Farina Benedetti Bernardi Cattaneo Donati Ferraro Gallo '
        'Guerra Monti Morelli Orlando Pace Riva Santoro Silvestri Valentini Zanetti Cirillo Amato De_Rosa '
        'Messina Basile Bellini Bassi Neri Carbone Grasso Pagano Marini Mazza Rossetti Sorrentino Tedesco '
        'Biondi Martini Ruggiero Pozzi Fumagalli Brambilla Ricciardi Coppola Valente'),
    'west-riding': group(
        'Hannah Martha Sarah Ann Mary Ellen Elizabeth Alice Emma Ruth Phoebe Mercy Esther Annie Ada Polly Edith '
        'Lizzie Jane Harriet Betty Nancy Grace Charlotte Susannah Rebecca Rachel Leah Miriam Keziah Rhoda '
        'Deborah Lydia Priscilla Tabitha Dinah Jemima Judith Naomi Abigail Patience Charity Prudence Emily '
        'Clara Florence Ethel Lilian Gertrude Maud Beatrice Mabel Elsie Nellie Minnie Gladys Amy Lucy Sally '
        'Kate Jessie Margaret Isabella Eliza Louisa Caroline Frances Fanny Selina Matilda Bertha Agnes Hilda '
        'Lily Rose Violet Ivy Daisy May Dorothy Sophia Catherine Hester Julia Edna Doris Mary_Ann Sarah_Ann '
        'Susan Betsy Bessie Zillah Lavinia Hephzibah Emmeline Clarissa Jessica Amelia Henrietta Rosa',
        'John William Joseph James Thomas George Samuel Benjamin Abraham Jonas Joshua Eli Fred Harold Albert '
        'Walter Tom Ned Henry Charles Edward Richard Robert Frank Harry Arthur Ernest Herbert Frederick Alfred '
        'Edwin Edgar Wilfred Willie Percy Sam Ben Jim Isaac Jacob Joel Josiah Jabez Enoch Elijah Elisha Ezra '
        'Amos Job Levi Reuben Seth Simeon Squire Hiram Moses Aaron Nathan Nathaniel Jonathan Matthew Mark Luke '
        'Michael David Daniel Abel Absalom Caleb Gideon Obadiah Zachariah Jeremiah Noah Asa Titus Uriah Edmund '
        'Lewis Clement Ellis Stanley Leonard Norman Cyril Clifford Allen Ambrose Jack Jesse Nehemiah Joe Dick '
        'Sidney Hubert Lister Ephraim Hezekiah Gilbert Oliver',
        '',
        'Sugden Ackroyd Holroyd Greenwood Sutcliffe Crowther Haigh Hirst Barraclough Firth Ramsden Wadsworth '
        'Butterworth Normanton Brearley Hinchliffe Pickles Shackleton Mitchell Booth Lumb Priestley Wormald '
        'Ingham Rushworth Dobson Sykes Lockwood Armitage Beaumont Brook Broadbent Hargreaves Holdsworth '
        'Illingworth Jowett Kershaw Lister Midgley Mortimer Naylor Oldroyd Pollard Redman Riley Robertshaw '
        'Schofield Senior Shaw Stansfield Sunderland Swift Thackray Townend Walshaw Whiteley Wilkinson Asquith '
        'Atkinson Bairstow Barker Bentley Binns Blackburn Boothroyd Bottomley Bradley Briggs Calvert Clayton '
        'Cockcroft Crabtree Dawson Denison Dyson Earnshaw Ellis Feather Gaukroger Gledhill Greaves Hainsworth '
        'Hartley Heaton Helliwell Hey Holmes Horsfall Hudson Jagger Kitson Laycock Lee Marsden Moorhouse Mellor '
        'Nutter Ogden Pearson Pickersgill'),
}

MEDIEVAL = {
    'norman': group(
        'Alice Isabel Matilda Joan Margery Agnes Emma Juliana Petronilla Avice Cecily Rohese Sybil Beatrice '
        'Eleanor Mabel Margaret Hawise Amice Constance Adeliza Ela Lucy Eva Basilia Maud Gundreda Aline '
        'Clemence Nichola Idonea Adela Aveline Agatha Amabel Christiana Denise Dionisia Ermengarde Euphemia '
        'Felicia Ida Laura Letitia Muriel Olive Philippa Rose Sabina Theophania Adelina Annora Ascelina Clarice '
        'Emeline Ermentrude Eustacia Gunnora Hersent Juetta Katherine Lescelina Millicent Mirabel Sarra '
        'Scholastica Tiffany Ismay Yolande Blanche Christina Rosamund Joanna Lauretta Isabella Albreda Galiena '
        'Elizabeth Annabel Osanna Lucia',
        'William Robert Richard Ralph Hugh Walter Geoffrey Roger Gilbert Henry Simon Thomas Nicholas Baldwin '
        'Reginald Guy Hamo Ranulf Eustace Fulk Alan Bertram Payn Roland Stephen Peter Philip Humphrey Miles '
        'Waleran Osbert Aubrey Amaury Anselm Arnulf Bartholomew Bernard Brian Drogo Ingram Everard Gerard '
        'Gervase Godfrey Herbert Hubert Ivo Jocelyn Lambert Maurice Matthew Odo Osbern Theobald Thurstan Warin '
        'Walkelin Adam Alexander Arnold Baldric Bertrand Hervey Ilbert Jordan Laurence Mauger Nigel Osmund '
        'Picot Savaric Serlo Tancred Urse Samson Saer Eudo Warner Engelard Lanfranc John Edmund Edward Gerald '
        'Hamelin Joscelin Andrew Michael Amfrid Unfrid Turold Gunfrid Wigan Rainald Fulcher Ernulf Roscelin '
        'Neel Fulbert Ernald',
        '',
        "de_Clare de_Lacy Mortimer Peverel Basset Beauchamp Mandeville Giffard Clifford Malet Ferrers Talbot "
        "de_Vere Bigod Percy Mowbray de_Warenne Fitzalan Courtenay Neville Despenser Grey de_Bohun Marshal "
        "de_Montfort Lovel Saint_John Bardolf Devereux Paynel de_Beaumont de_Braose de_Courcy de_Quincy de_Ros "
        "de_Say de_Stuteville de_Tosny de_Vesci de_Verdun de_Valence de_Lucy de_Burgh de_Brus Balliol de_Lisle "
        "Clinton Darcy Fiennes Gournay Harcourt Maltravers Montagu Montgomery Mohun Pipard Poynings Saint_Clair "
        "Saint_Leger Sackville Scrope Segrave Somery Stafford Tracy Umfraville Vavasour Venables Zouche "
        "Cantilupe Chaworth Corbet Crevecoeur Damory Engaine Fitzwalter Fitzwarin Fitzhugh Fitzwilliam "
        "Fitzherbert Fitzgerald Fitzosbern Furnival Glanville Gresley Hastings Hussey le_Strange Longchamp "
        "Marmion Mauduit Morville Pantulf Poyntz Raleigh Seymour Turberville Valoines Vipont d'Aubigny"),
    'english': group(
        'Agnes Alice Maud Edith Joan Emma Margery Christina Godiva Elfrida Wymarc Ellen Annot Tibb Mariot '
        'Isabel Cecily Juliana Matilda Margaret Katherine Lettice Amice Avice Sibyl Mabel Hawise Denise Felicia '
        'Rose Lucy Beatrice Gunnild Idonea Eva Alison Amabel Christian Clarice Constance Eleanor Goda Hilda '
        'Mildred Audrey Millicent Muriel Nicola Olive Parnel Philippa Sabina Susanna Elizabeth Anne Gillian '
        'Malkin Emmot Jenet Ida Rosamund Sarra Dulcia Agatha Marion Thomasina Benedicta Edeline Helen Aldith '
        'Edeva Leofrun Wulfrun Goldburga Thora Sigrid Margot Joanna Laura Ellota Magota Euphemia Annabel Mary '
        'Amy Petronilla Alviva Estrild Ragenild Aveline Gunnora Osanna Runild Scholastica Godeleva Aldiva '
        'Eunice',
        'John Thomas Adam Walter Wat Hob Robin Peter Simkin Edwin Godric Alfred Osric Wulfric Tom Dickon '
        'William Richard Robert Henry Roger Hugh Nicholas Ralph Geoffrey Gilbert Stephen Alan Simon Philip '
        'Laurence Jordan Elias Osbert Hamo Ranulf Gervase Martin Alexander Andrew Bartholomew Benedict Edmund '
        'Edward Edric Edgar Godwin Herbert Hubert Ivo Jocelin Lambert Matthew Maurice Michael Miles Nigel '
        'Oliver Osmund Piers Silvester Theobald Thurstan Warin Wulfstan Leofric Leofwine Aylwin Cuthbert '
        'Dunstan Oswald Siward Thurkill Colin Bennet Clement Denis Fulk Giles Gregory Guy Humphrey James Lucas '
        'Mark Samson Warner Baldwin Anselm Absalom Austin Christopher Daniel David Everard Ingram Jankin Jenkin '
        'Hick Hodge',
        '',
        'Atwood Miller Smith Baker Fletcher Carter Thatcher Webster Brewer Cooper Turner Shepherd Fisher Wright '
        'Chapman Mason Ward Fowler Gardner Bowyer Cook Taylor Skinner Tanner Dyer Hunt Reeve Glover Webb Walker '
        'Spencer Palmer Fuller Barker Attwell Bywater Underwood Archer Bailey Barber Bell Bishop Bond Bowman '
        'Brown Butcher Butler Carpenter Chandler Clark Collier Draper Freeman Godwin Granger Green Hayward Hill '
        'Hooper Kemp Knight Lambert Lane Lister Marshall Mercer Mills Naylor Page Parker Payne Plowman Potter '
        'Reed Roper Rowe Sadler Salter Sawyer Saunders Sexton Shearer Slater Spicer Stone Swift Thacker Tiler '
        'Tucker Wainwright Warner Weaver Wheeler White Wood Woodward Young Abbot Atwater Fairfax'),
    'welsh': group(
        'Gwen Angharad Nest Gwenllian Morfudd Eluned Tangwystl Lleucu Efa Generys Gwladus Dyddgu Mallt Margred '
        'Annes Gwerful Myfanwy Gwenhwyfar Elen Senena Ales Hunydd Gwenfrewi Mabli Iwerydd Cristin Euron Jonet '
        'Lowri Catrin Elliw Joan Elizabeth Eleanor Mary Rose Dorothy Juliana Amy Cecilia Tacy Emma Joyce '
        'Gwledyr Morfyl Erdudfyl Gwerydd Madrun Perweur Genilles Geneth Gwir Mabel Millicent Siwan Hawys '
        'Eurgain Erddylad Gaenor Gwenonwy Gwenddydd Dwynwen Isabel Alson Ellen Agnes Mererid Sioned',
        'Dafydd Rhys Owain Gruffudd Madog Iorwerth Llywelyn Hywel Ieuan Einion Cadwgan Maredudd Cynan Tudur '
        'Goronwy Ithel Bleddyn Rhodri Cadwaladr Morgan Trahaearn Ednyfed Phylip Gwilym Llywarch Meurig Cynwrig '
        'Heilyn Cadell Rhirid Seisyll Caradog Elidir Iago Adda Tegwared Gwion Madyn Griffri Ednowain Cydifor '
        'Iocyn Cyfnerth Morfran Deheuwynt Gwasdewi Llygad Idnerth Peredur Sulien Iolo Gwalchmai Cynddelw '
        'Deiniol Gwallter Gwgon Hwfa Ieuaf Maelgwn Meilyr Moreiddig Rhydderch Rhun Cadfan Cadwallon Ifor Morys '
        'Rheinallt Rhisiart Siencyn Hopcyn Tomos Lewys Rhiwallon Gwrgenau Bledri Cuhelyn Tudwal Iddon Ynyr '
        'Cynfyn Gwyn Gwenwynwyn Guto Gutun Deio Sion Wiliam',
        '',
        'ap_Rhys ap_Owain ferch_Madog Gwyn Llwyd Vychan Goch Ddu ap_Dafydd ap_Gruffudd ap_Ieuan ap_Hywel '
        'ap_Madog ap_Llywelyn ap_Einion ap_Iorwerth ap_Maredudd ap_Tudur ap_Cynwrig ap_Goronwy ap_Ithel '
        'ferch_Dafydd ferch_Rhys ferch_Gruffudd ferch_Ieuan ferch_Hywel Moel Bach Hir Crach Gethin ap_Gwilym '
        'ap_Rhodri ap_Cadwgan ap_Bleddyn ap_Cynan ap_Llywarch ap_Meurig ap_Morgan ap_Phylip ap_Adda ap_Iago '
        'ap_Trahaearn ap_Ednyfed ap_Caradog ap_Gwyn ap_Rhun ap_Rhydderch ap_Ifor ap_Morys ap_Hopcyn ap_Siencyn '
        'ap_Rhisiart ap_Meilyr ap_Gwgon ap_Cadwallon ap_Tudwal ap_Heilyn ap_Cadell ap_Seisyll ap_Elidir ap_Iolo '
        'ap_Deio ap_Gutun ap_Tomos ap_Ieuaf ap_Cadfan ap_Ynyr ap_Iddon ap_Bledri ferch_Owain ferch_Llywelyn '
        'ferch_Einion ferch_Iorwerth ferch_Maredudd ferch_Tudur ferch_Cynwrig ferch_Goronwy ferch_Ithel '
        'ferch_Gwilym ferch_Morgan ferch_Rhodri ferch_Cadwgan ferch_Bleddyn ferch_Llywarch ferch_Meurig '
        'ferch_Phylip ferch_Adda Gam Sais Gloff Wyddel Tew Ieuanc Hael Mawr Gryg Benfras Teg Hen'),
}

FRONTIER = {
    'american': group(
        'Mary Sarah Martha Hattie Lizzie Nancy Lucinda Mattie Emma Ida Josephine Belle Clara Laura Minnie Sadie '
        'Cora Nellie Pearl Effie Elizabeth Anna Margaret Ellen Catherine Jane Susan Rebecca Rachel Rhoda Lydia '
        'Harriet Ann Eliza Louisa Julia Frances Fannie Lucy Alice Annie Bessie Jennie Maggie Lula Lottie Ella '
        'Ada Flora Florence Etta Nettie Rosa Lillie Mollie Callie Dora Della Eva Grace Hannah Abigail Amanda '
        'Matilda Malinda Melissa Delilah Charlotte Caroline Lavinia Mahala Permelia Parthenia Elvira Virginia '
        'Georgia Vinnie Viola Kate Cynthia Sallie Polly Susannah Priscilla Phoebe Ruth Esther Agnes Augusta '
        'Adeline Orpha Olive Lena Almira Emeline Hester Lettie Hettie Ollie Ophelia',
        'John James William George Charles Henry Thomas Samuel Joseph Wyatt Jesse Amos Silas Lafayette Elijah '
        'Ezra Calvin Ben Lem Jim Robert Edward David Daniel Andrew Benjamin Isaac Jacob Joshua Nathan Nathaniel '
        'Levi Lewis Marion Martin Walter Frank Harry Albert Alfred Edwin Frederick Richard Francis Hiram Asa '
        'Abner Absalom Alonzo Alvin Ambrose Archibald Augustus Cyrus Clay Eli Elisha Emmett Enoch Ephraim '
        'Erastus Ethan Felix Gideon Granville Harrison Harvey Hezekiah Horace Isom Jasper Jefferson Jeremiah '
        'Jonas Josiah Leander Lemuel Lorenzo Lucius Luther Marcus Micajah Milton Moses Newton Noah Oliver '
        'Orville Oscar Perry Philip Reuben Rufus Sampson Seth Stephen Sterling Thaddeus Theodore Ulysses',
        '',
        'Clanton Hughes Bradshaw Pruitt Tolliver Haskell Whitfield Gentry Burris Coffey Rutledge Spence Dunlap '
        'Crenshaw Harlan Fenton Rhodes McKinney Baird Bascom Puckett Yancey Smith Johnson Williams Brown Jones '
        'Davis Miller Wilson Moore Taylor Anderson Thomas Jackson White Harris Martin Thompson Allen Young '
        'Walker Wright Hill Scott Green Adams Baker Nelson Carter Mitchell Campbell Roberts Parker Evans Turner '
        'Collins Cook Bell Ward Cox Howard Brooks Gray Reed Price Barnes Ross Henderson Coleman Jenkins Perry '
        'Powell Long Patterson Foster Russell Griffin Hayes Ford Hamilton Graham Wallace Woods Cole West Owens '
        'Reynolds Fisher Ellis Harrison Gibson Marshall Wells Simpson Stevens Tucker Porter Hunter Hicks'),
    'mexican': group(
        'Maria Josefa Refugio Guadalupe Dolores Manuela Juana Soledad Petra Ramona Trinidad Carmen Francisca '
        'Antonia Rosa Teresa Luz Paula Rafaela Concepcion Encarnacion Ignacia Jesusa Gertrudis Isabel Ana Rita '
        'Lugarda Mercedes Altagracia Marcelina Feliciana Leonor Victoria Margarita Juliana Luisa Micaela Marta '
        'Brigida Catalina Clara Barbara Andrea Josefina Eulalia Gregoria Dominga Tomasa Agustina Rosalia Susana '
        'Ines Apolonia Benita Candelaria Casimira Crescencia Damiana Estefana Eusebia Faustina Felipa '
        'Florentina Gabriela Inocencia Jacinta Leocadia Lorenza Lucia Macaria Marcela Martina Matilde Natividad '
        'Nicolasa Pascuala Paulina Pilar Prudencia Rosario Sabina Serafina Simona Valentina Vicenta Elena '
        'Eugenia Beatriz Anastasia Asuncion Candida Celestina Cipriana Delfina Dorotea Epifania Fermina Hilaria '
        'Maria_Antonia',
        'Jose Juan Manuel Francisco Jesus Ignacio Pedro Ramon Antonio Santiago Esteban Rafael Miguel Jose_Maria '
        'Luis Tomas Joaquin Felipe Andres Agustin Vicente Cristobal Julian Bernardo Teodoro Marcos Nicolas '
        'Mariano Lorenzo Gregorio Ysidro Tiburcio Atanacio Bartolo Anastasio Diego Alejandro Blas Benito '
        'Bonifacio Calixto Candelario Carlos Cayetano Cipriano Dionisio Domingo Eusebio Eugenio Faustino '
        'Feliciano Felix Fernando Gabriel Hilario Jacinto Jeronimo Leandro Lucas Marcelino Martin Matias '
        'Melquiades Pablo Pascual Policarpo Rosendo Salvador Santos Saturnino Sebastian Simon Valentin Ventura '
        'Victoriano Zeferino Apolonio Aniceto Ambrosio Abundio Bernabe Crecencio Desiderio Eleuterio Epifanio '
        'Estanislao Eulogio Fermin Gervasio Hermenegildo Jose_Antonio Jose_Manuel Juan_de_Dios Justo Leonardo '
        'Macario Modesto Narciso Patricio Prudencio',
        '',
        'Romero Elias Ochoa Pacheco Ortiz Telles Leon Aguirre Robles Samaniego Contreras Salazar Montoya Garcia '
        'Martinez Lopez Sanchez Chavez Vigil Lucero Baca Sandoval Archuleta Valdez Gallegos Armijo Otero Luna '
        'Sena Trujillo Gonzales Duran Moreno Estrada Carrillo Hernandez Perez Rodriguez Ramirez Torres Flores '
        'Rivera Gomez Diaz Morales Reyes Cruz Gutierrez Ramos Mendoza Ruiz Alvarez Castillo Jimenez Vargas '
        'Herrera Medina Aguilar Vega Castro Delgado Padilla Apodaca Arguello Bustamante Cordova Espinosa '
        'Fernandez Gurule Jaramillo Maestas Mondragon Olguin Ortega Quintana Rael Salas Serna Silva Tafoya '
        'Tapia Ulibarri Valencia Velasquez Zamora Abeyta Anaya Atencio Benavides Cisneros Esquibel Galindo '
        'Lovato Madrid Manzanares Molina Montano Muniz Nunez Rivas'),
    'cornish': group(
        'Jenefer Mary Elizabeth Grace Thomasine Loveday Jane Kitty Ann Mary_Ann Honour Philippa Wilmot Tamsin '
        'Patience Prudence Jenny Emily Eliza Catherine Susan Martha Charity Mercy Sarah Hannah Ellen Harriet '
        'Emma Bessie Annie Johanna Alice Agnes Dorcas Dorothy Joan Joanna Keziah Lavinia Lydia Margery Margaret '
        'Maria Christian Constance Damaris Eleanor Gertrude Isabella Julia Louisa Lucy Nancy Ruth Rebecca '
        'Selina Sophia Susanna Tryphena Tabitha Temperance Ursula Zenobia Blanche Frances Fanny Rosina Amelia '
        'Ada Caroline Charlotte Clara Edith Elsie Eva Florence Jessie Kate Laura Lilian Mabel Matilda Minnie '
        'Nellie Rachel Rhoda Thirza Jemima Mary_Jane Avis Esther Phillis Hephzibah Loveday_Ann Elizabeth_Ann '
        'Grace_Ann Emily_Jane Lily Henrietta',
        'John Richard William Nicholas Josiah Hart Jabez Thomas Samuel Edward James Henry Joseph George Peter '
        'Stephen Francis Matthew Philip Charles Simon Benjamin Joel Elisha Ezekiel Digory Hannibal Mark Michael '
        'Paul Abraham Jacob Silas Walter Anthony Arthur Alfred Albert Caleb Daniel David Edwin Enoch Ephraim '
        'Frederick Hezekiah Humphrey Isaac Jonathan Joshua Jethro Levi Lewis Martin Moses Nathaniel Noah '
        'Obadiah Oliver Reuben Robert Ralph Shadrach Theophilus Tobias Uriah Absalom Amos Archelaus Bennet '
        'Christopher Clement Edmund Ebenezer Eli Elijah Frank Harry Herbert Hugh Jasper Jonas Justinian '
        'Nehemiah Pentecost Sampson Simeon Solomon Tristram Vivian Zebedee Zacharias Jenkin Ezra Hender Malachi '
        'Ambrose Nathan Gilbert Andrew',
        '',
        'Trevithick Penrose Polglase Tregear Pascoe Trelawny Nankivell Rowe Bolitho Pengelly Tremayne Chenoweth '
        'Trevena Trethewey Tregonning Penhaligon Pendarves Jory Jago Hocking Hosking Williams Rule Nance Oates '
        'Tonkin Uren Rodda Curnow Trewartha Kitto Polkinghorne Spargo Dunstan Angove Bawden Berryman Bray Carne '
        'Chegwidden Couch Cundy Dingle Eddy Glasson Gilbert Hambly Harvey Hicks Hoskin Jenkin Kemp Lander '
        'Lanyon Laity Mitchell Nancarrow Opie Paull Pearce Penberthy Pender Pentreath Pengilly Phillips Prowse '
        'Quick Retallack Roberts Sampson Stephens Teague Thomas Treloar Tregenza Tremewan Trengove Trewin '
        'Trezise Tyack Varcoe Vosper Wearne Woolcock Bennetts Gluyas Grenfell Jewell Keast Kneebone Lobb Martyn '
        'Moyle Nicholls Olver Penhale Rosevear Sobey Symons Tamblyn'),
    'irish': group(
        'Bridget Mary Margaret Annie Kate Nora Ellen Catherine Johanna Honora Julia Ann Mary_Ann Elizabeth '
        'Delia Winifred Sarah Hannah Alice Teresa Agnes Rose Jane Eliza Maggie Lizzie Nellie Bessie Abbie Susan '
        'Josephine Celia Peggy Molly Katie Minnie Ellie Jenny Nancy Sally Biddy Kathleen Frances Fanny Isabella '
        'Sophia Martha Maria Cecilia Monica Anastasia Deborah Penelope Una Grace Helena Helen Esther Emily '
        'Louisa Margery Barbara Lucy Letitia Philomena Bernadette Agatha Rosanna Eleanor Mabel Amelia Charlotte '
        'Harriet Caroline Matilda Judith Joanna Emma Laura Lena Jessie Edith Alicia Marcella Polly Betty '
        'Florence Dorothy Rebecca Clara Gertrude Eileen Kitty Christina Sabina Abina Mamie Nora_Ann Ella '
        'Theresa',
        'Patrick Michael Dennis Timothy Cornelius Owen Daniel John James Thomas William Edward Bartholomew '
        'Jeremiah Terence Hugh Martin Peter Francis Joseph Bernard Matthew Laurence Andrew Charles Richard '
        'Maurice Myles Felix Edmund Thady Barney Eugene Denis Darby Dermot Jerome Garrett Gerald Henry Luke '
        'Mark Morgan Nicholas Philip Robert Roger Stephen Simon Malachy Murtagh Neil Mortimer Anthony Ambrose '
        'Alexander Arthur George Paul Pierce Redmond Raymond Ulick Brian Manus Dominick Colman Godfrey Oliver '
        'Samuel Sylvester Theobald Valentine Vincent Walter Randal Albert Alfred Austin Benjamin Frederick '
        'Louis Christopher Lawrence Matthias Constantine Malachi Moses Harry Frank Ned Mick Dan Tim Jerry Larry '
        'Mike Pat Ellis David',
        '',
        "O'Rourke Sweeney Daly Hogan Mahoney Riordan Cassidy Moran Sullivan Murphy O'Brien Kelly Ryan Walsh "
        "Kennedy McCarthy Donovan Burke Fitzgerald Carroll Nolan Quinn Connolly Dwyer Kearney Duffy Lynch "
        "McGrath Shea Hennessy Brady Tobin Collins O'Connor Murray Dunne Power Dempsey Farrell Gallagher "
        "Doherty Boyle Maguire McLoughlin Kane Devlin Kenny Reilly Clarke Keogh Whelan Foley Hurley Mullins "
        "O'Donnell Rooney McDonnell Flanagan Duggan Hickey Coleman Cullen Barry Ahern Barrett Butler Costello "
        "Cronin Crowley Cummins Curran Delaney Dillon Dolan Donnelly Doran Egan Fahy Finnegan Gleeson Griffin "
        "Hanlon Higgins Horgan Keating Lawlor Lennon Lyons McCormack McKenna McMahon Madden Maher Mooney "
        "Mulcahy Mulligan Noonan O'Donoghue O'Keeffe Phelan"),
    'german': group(
        'Anna Katharina Margaretha Elisabeth Louisa Wilhelmina Emma Maria Christina Sophia Barbara Magdalena '
        'Dorothea Friederike Caroline Johanna Bertha Amalia Paulina Rosina Augusta Mathilde Theresa Clara Lina '
        'Minna Ida Helena Henriette Charlotte Frieda Eva Agnes Albertina Babette Cecilia Dora Elise Ella Emilie '
        'Ernestine Franziska Gertrud Hedwig Hermine Josephine Juliana Justine Kunigunde Lena Lisette Lydia '
        'Martha Ottilie Regina Rosalie Sabina Selma Sibylla Susanna Ursula Veronika Walburga Adelheid Agathe '
        'Apollonia Brigitta Elsa Gretchen Hanna Irma Josepha Lotte Lucia Tekla Viktoria Eleonore Gisela Hulda '
        'Irene Klothilde Leonore Meta Olga Rebekka Salome Marie Luise Katharine Margarethe Christine Theresia '
        'Sophie Pauline Louise Friedericke Karoline Annie Mary Lizzie',
        'Johann Friedrich Heinrich Wilhelm Karl August Otto Georg Jakob Philipp Peter Ludwig Christian Adam '
        'Konrad Michael Franz Joseph Hermann Gottlieb Ernst Gustav Martin Andreas Valentin Anton Fritz '
        'Christoph Nikolaus Matthias Adolph Rudolph Albert Balthasar Benedikt Bernhard Daniel David Dietrich '
        'Eduard Emil Erhard Felix Ferdinand Gerhard Gottfried Gottlob Hans Hugo Ignatz Julius Kaspar Leonhard '
        'Leopold Lorenz Lukas Markus Max Moritz Oskar Paul Reinhold Richard Robert Sebastian Simon Stephan '
        'Theodor Thomas Traugott Ulrich Urban Victor Walter Werner Wendelin Wolfgang Xaver Alois Arnold Bruno '
        'Clemens Engelbert Eugen Fridolin Gebhard Hubert Isidor Kilian Lambert Lothar Melchior Oswald Reinhard '
        'Siegfried Theobald Vinzenz Wenzel Albrecht Hieronymus',
        '',
        'Schmidt Becker Vogel Hartmann Kessler Lutz Brunner Weber Zimmermann Mueller Schneider Fischer Meyer '
        'Wagner Schulz Hoffmann Koch Bauer Richter Klein Wolf Schroeder Neumann Schwarz Braun Krueger Hofmann '
        'Lange Werner Krause Meier Lehmann Fuchs Keller Jung Hahn Schubert Vogt Friedrich Scholz Boehm Martin '
        'Schumacher Frank Berger Winkler Roth Beck Lorenz Baumann Franke Albrecht Schuster Simon Ludwig Winter '
        'Kraft Schumann Haas Seidel Heinrich Brandt Kuhn Busch Pohl Horn Arnold Sauer Engel Kaiser Ziegler Graf '
        'Dietrich Herrmann Huber Mayer Schreiber Peters Jaeger Gross Ernst Hess Otto Pfeiffer Ritter Stein '
        'Schaefer Sommer Stahl Thiel Ulrich Voigt Walter Wendt Eckert Gerber Hauser Koenig Metzger Nagel'),
    'chinese': group(
        'Ah_Ying Mei_Lan Gum_Moy Sing_Toy Lai_Ho Ah_Toy Ah_Moy Ah_Kum Ah_Lan Ah_Yuk Ah_Hoy Ah_Choy Ah_Sue Ah_Ho '
        'Ah_Yoke Ah_Fah Ah_Ngan Ah_Kew Ah_Chun Ah_Lin Gum_Ying Kum_Ho Yut_Ho Yee_Toy Sing_Moy Lin_Moy Kum_Fong '
        'Lai_Ying Fung_Moy Choy_Lin Moy_Ying Yuen_Kum Sue_Kum Ah_Kim Ah_Mui Ah_Oy Ah_Wan Ah_Yee Ah_Ling Ah_Kwai '
        'Ah_Fung Ah_Gum Mei_Ying Kum_Lin Sue_Ying Yuk_Ying Ah_Lai Ah_Mei Ah_Ngoon Ah_Sum Kum_Ying Lin_Ho '
        'Yee_Moy',
        'Ah_Sam Wing Chung Fook Quong Hop_Kee Sing Ah_Sing Ah_Lee Ah_Kee Ah_Wing Ah_Fong Ah_Chung Ah_Hing '
        'Ah_Quong Ah_Yen Ah_Fook Ah_Louie Ah_Chew Ah_Gow Ah_Hop Ah_Jim Ah_Tom Hong Hing Kee Lung Chew Yuen Bing '
        'Gong Tong Fat Quan Yick Ah_Wah Ah_Ming Ah_Soon Ah_Tong Ah_Chong Ah_Fat Ah_Gee Ah_Bow Ah_Lum Ah_Hong '
        'Ah_Yung Ah_Kim Ah_Wo Ah_Chee Ah_Ying Ah_Foo Wah Ming Chong Soon Foo Look Gee Lum Hop Sang Yee Kim Sun '
        'Ying Hoy Gim Woo Kwong Sam Tung Lai Ah_Ngan Ah_Sang Ah_Look Ah_Tung',
        '',
        'Lee Wong Chan Chin Yee Ng Fong Louie Moy Lum Fung Quan Leong Gin Tom Jue Dea Toy Hom Woo Eng Yuen Hong '
        'Lau Mah Poon Chew Dong Joe Gee Kwong Jung Tsui Suen Ko Cheng Tse Sung Hon Cho Tsang Siu Tin Tung Choi '
        'Tseung Yue To Ngai So Lui Ting Yam Yiu Fu Keung Chui Fan Luk Shek Tai Ha Yau Hau Chau Mang Pak Yim '
        'Tuen Sze Mo Ku Kok Kung Man Heung Chang Chung Cheung Ho Kwan Lai Leung Lo Pang Tam Tang Yip Yu Au Choy '
        'Chow Fok Hui Kam Lam Lew Low Mak Mok'),
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

STORYBOOK = {
    'plain': group(
        'Hester Marigold Tansy Prudence Wilhelmina Bettony Dulcie Maud Bess Ottilie Hazel Posy Clemency Ada '
        'Bryony Winnie Lettice Nell Tibby Gwendolyn Agnes Alice Annie Beatrice Betsy Clara Constance Cicely '
        'Daisy Dora Dorothy Edith Elsie Emily Esther Ethel Eliza Fanny Flora Florence Gertie Grace Hannah '
        'Harriet Henrietta Hilda Honor Ivy Jane Jemima Kate Kitty Lavinia Lily Lizzie Lottie Lucy Mabel Martha '
        'Mary Matilda May Meg Mercy Mildred Millie Minnie Molly Nancy Nettie Olive Patience Peggy Phoebe Polly '
        'Primrose Rose Rosie Ruth Sally Sarah Susan Tabitha Temperance Violet Winifred Bella Bertha Effie Edna '
        'Emma Joan Lettie Marjorie Maisie Mattie Nora Pansy Pearl Poppy',
        'Tobin Bram Hob Wendel Barnaby Ambrose Jory Ned Ferris Osgood Pip Cuthbert Dunstan Rollo Jasper Ezekiel '
        'Lem Horace Bartholomew Wilbur Abel Albert Alfred Amos Arthur Barney Basil Ben Bertie Cecil Clement '
        'Edmund Edgar Edwin Eli Ernest Fred Frederick George Gilbert Giles Harry Herbert Hugh Isaac Jack Jacob '
        'Jethro Joe Jonah Josiah Joseph Lewis Luke Matthew Nat Noah Oliver Oswald Percy Peter Reuben Roger '
        'Rufus Sam Seth Silas Simon Stanley Thomas Tom Walter Wat Will Wilfred Bertram Godfrey Humphrey Toby '
        'Archie Alfie Ezra Enoch Obadiah Septimus Benedict Christopher Daniel Felix Gabriel Henry James John '
        'Martin Nicholas Owen Ralph Robert Rowland Stephen',
        'Robin Kit Jem Frankie',
        'Thistlewood Puddifoot Hobbs Mossley Applegarth Wickham Fennimore Crumb Featherstone Tillbrook Underhay '
        'Oakshott Fairweather Cotton Tanner Pickering Dimmock Hobday Gammage Ottley Brewster Cobb Pennington '
        'Ashby Goodbody Littlejohn Shepherd Weaver Hatcher Merriman Appleby Ashworth Baxter Bellamy Birch '
        'Blackmore Bramley Brook Bunting Butterfield Chandler Cherry Cobbold Cotterill Cowley Crabtree Dale '
        'Dewhurst Drinkwater Dunn Fairclough Farley Fenwick Fletcher Foxley Gardner Garland Goodall Goodwin '
        'Hardcastle Hartley Hawthorn Hayward Heron Hickling Hollins Honeyman Hopkins Kettle Lamb Larkin Lovell '
        'Lowe Meadows Merryweather Middleton Miller Nettleton Norbury Oakley Orchard Partridge Peabody Plumb '
        'Pocock Popplewell Puddephat Rook Rowntree Sadler Sawyer Shipley Sparrow Starling Stubbs Swallow '
        'Thackeray Thatcher Tinker Tomkins'),
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

# A Roman woman carries her family's name in its feminine form (Julius, Julia).
for roman in ANCIENT_ROME.values():
    roman['feminine_family'] = {'ius': 'ia', 'us': 'a'}

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
