import os
import zmq
import json
import time
import argparse
import numpy as np
from tqdm import tqdm
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import itertools
from mendeleev import element
from termcolor import colored
import pyfiglet


def get_parser():

    parser = argparse.ArgumentParser(description = 'Plotting script')

    parser.add_argument('-Talys',
                        dest='Talysfolder',
                        type=str,
                        help='Talys simulation folder')

    parser.add_argument('-PACE',
                        dest='PACEfolder',
                        type=str,
                        help='PACE4 simulation folder')

    parser.add_argument('-EXFOR',
                        dest='EXFORfolder',
                        type=str,
                        help='EXFOR experimental data folder')

    parser.add_argument('-o',
                        dest='Outfolder',
                        type=str,
                        help='output folder')


    args = parser.parse_args()

    return args, parser

#def extract_EXS(filename):

def Talys_rpExtractor(SimulationDIR):

    rpData = dict()

    for folder in tqdm(os.listdir(SimulationDIR)):
        if ( folder.find('Energy_') != -1 ) :
            #print('------',folder,'------')
            for isotope in os.listdir(SimulationDIR+'/'+folder):
                if ( isotope.find('rp') != -1 and isotope.find('.tot') != -1) :
                    IsoKey = isotope[2:8]
                    data = np.loadtxt(SimulationDIR+'/'+folder+'/'+isotope)
                    if (rpData.get(IsoKey) == None) :
                        rpData[IsoKey] = [ [data[0]],[data[1]] ]
                    else:
                        rpData[IsoKey][0].append(data[0])
                        rpData[IsoKey][1].append(data[1])

    return rpData

def Talys_recExtractor(SimulationDIR):

    recData = dict()

    for folder in tqdm(os.listdir(SimulationDIR)):
        if ( folder.find('Energy_') != -1 ) :
            Energy = '{:03d}'.format(int(folder[7:]))
            for isotope in os.listdir(SimulationDIR+'/'+folder):
                if ( isotope.find('rec') != -1 and isotope.find('.tot') != -1) :
                    IsoKey = isotope[3:9]
                    data = np.loadtxt(SimulationDIR+'/'+folder+'/'+isotope)

                    if (recData.get(IsoKey) == None) :
                        recData[IsoKey] = dict()
                        cycleflag = True
                        list_tmp = []
                        for line in data:
                            if cycleflag:
                                list_tmp = [ [line[0]], [line[1]]]
                                cycleflag = False
                            else:
                                list_tmp[0].append(line[0])
                                list_tmp[1].append(line[1])
                        recData[IsoKey][Energy] = list_tmp[:]
                    else:
                        cycleflag = True
                        list_tmp = []
                        for line in data:
                            if cycleflag:
                                list_tmp = [ [line[0]], [line[1]]]
                                cycleflag = False
                            else:
                                list_tmp[0].append(line[0])
                                list_tmp[1].append(line[1])
                        recData[IsoKey][Energy] = list_tmp[:]

    return recData

def PACE_rpExtractor(SimulationDIR):

    rpData = dict()

    for files in tqdm(os.listdir(SimulationDIR+'/xsec')):
            Energy = 10 + 5*(int(files[-6:-4])-1)
            data = np.loadtxt(SimulationDIR+'/xsec/'+files,comments='!')
            if (len(data.shape) == 1):
                IsoKey = '{:03d}'.format(int(data[0]))+'{:03d}'.format(int(data[0]+data[1]))

                if (rpData.get(IsoKey) == None) :
                    rpData[IsoKey] = [ [Energy],[data[2]] ]
                else:
                    rpData[IsoKey][0].append(Energy)
                    rpData[IsoKey][1].append(data[2])
            else:
                for entry in data:
                    IsoKey = '{:03d}'.format(int(entry[0]))+'{:03d}'.format(int(entry[0]+entry[1]))

                    if (rpData.get(IsoKey) == None) :
                        rpData[IsoKey] = [ [Energy],[entry[2]] ]
                    else:
                        rpData[IsoKey][0].append(Energy)
                        rpData[IsoKey][1].append(entry[2])

    return rpData

def PACE_recExtractor(SimulationDIR):

    recData = dict()

    for files in tqdm(os.listdir(SimulationDIR+'/simufiles')):
            if (files.find('.particles') != -1 ):
                Energy = '{:03d}'.format(10 + 5*(int(files[-12:-10])-1))
                data = np.loadtxt(SimulationDIR+'/simufiles/'+files, skiprows = 2, usecols = (4,5,6,7,14)) #4-Zf 5-Nf 6-Zc 7-Nc 14-Ep_Lab
                for line in data:
                    IsoKey = '{:03d}'.format(int(line[0]))+'{:03d}'.format(int(line[0]+line[1]))

                    if (recData.get(IsoKey) == None) :
                        recData[IsoKey] = dict()
                        recData[IsoKey][Energy] = [line[4]]
                    elif (recData[IsoKey].get(Energy) == None) :
                        recData[IsoKey][Energy] = [line[4]]
                    else :
                        recData[IsoKey][Energy].append(line[4])

    return recData

def EXFOR_Extractor(DIR):

    rpData = dict()

    for files in os.listdir(DIR):
        IsoKey = files[0:6]
        with open(DIR+'/'+files) as fp:
            titlekey = ''
            dataflag = False
            cycleflag = True
            DataList_tmp = []

            for line in fp:
                if (line[0:2] == '//') :
                    dataflag = False
                    if (rpData.get(titlekey) == None) :
                        rpData[titlekey] = dict()
                    rpData[titlekey][IsoKey] = DataList_tmp[:]
                    DataList_tmp.clear()
                    titlekey = ''

                if (line[0] != '#' and dataflag) :
                    data = line.strip().split(' ')

                    if ( cycleflag ) :
                        DataList_tmp = [ [float(data[0])], [float(data[1])], [float(data[2])]]
                        cycleflag = False

                    else :
                        DataList_tmp[0].append(float(data[0]))
                        DataList_tmp[1].append(float(data[1]))
                        DataList_tmp[2].append(float(data[2]))


                if (line[0:4] == 'tit:') :
                    titlekey = line[5:-1]
                    dataflag = True
                    cycleflag = True



    return rpData

def edgefinder(IsoList):

    Zlist = []
    Nlist = []
    for key in IsoList:
        if (int(key[0:3])-0.5 not in Zlist):
            Zlist.append(int(key[0:3])-0.5)
        if ((int(key[3:6])-int(key[0:3])-0.5) not in Nlist):
            Nlist.append(int(key[3:6])-int(key[0:3])-0.5)

    Zlist.sort()
    Nlist.sort()
    Zlist.append(Zlist[-1]+1)
    Nlist.append(Nlist[-1]+1)
    return [Nlist,Zlist]

def histolister(rpData, energy):
    x = []
    y = []
    w = []
    for key in rpData.keys():
        try:
            index = rpData[key][0].index(energy)
            x.append(int(key[3:6])-int(key[0:3]))
            y.append(int(key[0:3]))
            w.append(rpData[key][1][index])
        except:
            continue



    return x, y, w

def keysorter(rpData):
    keyList = []
    for key in rpData.keys():
        keyList.append(key)
    keyList.sort()
    return keyList

def listsorter(X,Y):
    list1, list2 = zip(*sorted(zip(X,Y)))
    Xlist, Ylist = (list(t) for t in zip(*sorted(zip(list1, list2))))
    return Xlist, Ylist

def segreplotter(outfolder,code,rpData):
    print('------Plotting segre plot for ',code,'------')
    for energy in range(20,140,5):

        keyList = []
        for key in rpData.keys():
            keyList.append(key)

        keyList.sort()

        BIN = edgefinder(keyList)
        N, Z, W = histolister(rpData,energy)

        hist, xbins, ybins, im = plt.hist2d(N,Z,bins=BIN, weights=W, cmap='autumn', norm=LogNorm(vmin=0.001, vmax=max(W)))

        Title =  str(energy)+' MeV'
        outfile = outfolder+'/SEGRESIM/'+code+'/Energy_'+str(energy)+'.png'

        plt.title(Title)
        plt.xlabel("N")
        plt.ylabel("Z")


        cbar = plt.colorbar()
        cbar.set_label("Cross Section [mb]")
        print('Segre chart for energy -> ',energy)
        for i in range(len(ybins)-1):
            for j in range(len(xbins)-1):
                El = element(int(ybins[i]+0.5))
                label = str(int(xbins[j]+0.5+ybins[i]+0.5))+El.symbol
                if(hist.T[i,j]): plt.text(xbins[j]+0.5,ybins[i]+0.5, label, color="k", ha="center", va="center",fontsize = 4)

        plt.savefig(outfile,dpi = 300)
        plt.close()

def clear():
    os.system('clear')

def menu():
        strs = ('Enter 1 for plotting Segre production charts\n'
                'Enter 2 for plotting EXFOR data comparison\n'
                'Enter 3 for plotting Simulated production Cross Sections\n'
                'Enter 4 for plotting Recoil spectra\n'
                'Enter 5 to exit : ')
        choice = input(strs)
        return int(choice)


def main():

    clear()
    ascii_banner = pyfiglet.figlet_format("Simulation Data Sorter")
    print(ascii_banner)
    #-----Getting parser-----#
    args, parser = get_parser()

    #-----Define data containers-----#
    rpTalysData = dict()
    rpPACEData = dict()
    rpEXFORData = dict()

    #-----retrieve data from dataset-----#
    if args.Talysfolder is not None:
        print('--Sorting ',colored('Talys', 'green'),' Data--')
        rpTalysData = Talys_rpExtractor(args.Talysfolder)
    else:
        print(colored('WARNING :', 'yellow'), ' Talys Data not provided')

    if args.PACEfolder is not None:
        print('--Sorting ',colored('PACE4', 'green'),' Data--')
        rpPACEData = PACE_rpExtractor(args.PACEfolder)
    else:
        print(colored('WARNING :', 'yellow'), ' PACE4 Data not provided')

    if args.EXFORfolder is not None:
        print('--Sorting ',colored('EXFOR', 'green'),' Data--')
        rpEXFORData = EXFOR_Extractor(args.EXFORfolder)
    else:
        print(colored('WARNING :', 'yellow'), ' EXFOR Data not provided')

    if args.Outfolder is not None:
        print('--Output folder is -> ', os.path.abspath(args.Outfolder))
        try:
            os.mkdir(args.Outfolder)
        except:
            print(colored('WARNING :', 'yellow'),args.Outfolder," already exist")
    else:
        print(colored('ERROR :', 'red'), 'Output folder not provided')
        raise SystemExit


    while True:
        clear()
        print(ascii_banner)
        choice = menu()


        if choice == 1:
            clear()
            print(ascii_banner)
            try:
                os.mkdir(args.Outfolder+"/SEGRESIM")
            except:
                print(colored('WARNING :', 'yellow')," Segre plot already exist. All content will be replaced")
            finally:
                os.system('rm -r '+args.Outfolder+"/SEGRESIM")
                os.mkdir(args.Outfolder+"/SEGRESIM")

            if args.Talysfolder is not None:
                os.mkdir(args.Outfolder+"/SEGRESIM/Talys")
                segreplotter(args.Outfolder,'Talys',rpTalysData)
            if args.PACEfolder is not None:
                os.mkdir(args.Outfolder+"/SEGRESIM/PACE")
                segreplotter(args.Outfolder,'PACE',rpPACEData)

        elif choice == 2:
            clear()
            print(ascii_banner)

            EXFORauthorList = []
            EXFORIsokeyList = []
            TalyskeyList    = []
            PACEkeyList     = []
            CN = ''
            while True:
                CN = input('Insert CN [ZZZAAA] : ')
                if (len(CN) == 6): break
                print(colored('WARNING :', 'yellow')," Wrong CN format")

            #-----sort produced istopes-----#
            if args.Talysfolder is not None:
                TalyskeyList = keysorter(rpTalysData)
            else:
                print(colored('ERROR :', 'red'), ' Talys Data not provided')
                raise SystemExit

            if args.PACEfolder is not None:
                PACEkeyList = keysorter(rpPACEData)
            else:
                print(colored('ERROR :', 'red'), ' PACE Data not provided')
                raise SystemExit

            if args.EXFORfolder is not None:
                EXFORauthorList = []
                EXFORIsokeyList = []
                for key in rpEXFORData.keys():
                    EXFORauthorList.append(key)
                    for isokey in rpEXFORData[key].keys():
                        if (isokey in EXFORIsokeyList): continue
                        else: EXFORIsokeyList.append(isokey)
                EXFORauthorList.sort()
                EXFORIsokeyList.sort()
            else:
                print(colored('ERROR :', 'red'), ' EXFOR Data not provided')
                raise SystemExit


            CommonIsoKeyEXP = []
            for key in rpPACEData.keys():
                if key in rpTalysData:
                    if key in EXFORIsokeyList:
                        CommonIsoKeyEXP.append(key)

            CommonIsoKeyEXP.sort()
            try:
                os.mkdir(args.Outfolder+"/EXPSIM")
            except:
                print(colored('WARNING :', 'yellow')," Comparison plots already exist. All content will be replaced")
            finally:
                os.system('rm -r '+args.Outfolder+"/EXPSIM")
                os.mkdir(args.Outfolder+"/EXPSIM")


            marker = itertools.cycle(('s', 'p', 'o'))
            color = itertools.cycle(('m', 'b'))

            for key in CommonIsoKeyEXP:
                print('------Plotting production Cross Section for ',key,'------')
                outfile = args.Outfolder+'/EXPSIM/'+key+'.png'
                #sorting
                X1, Y1 = listsorter(rpPACEData[key][0], rpPACEData[key][1])
                X2, Y2 = listsorter(rpTalysData[key][0], rpTalysData[key][1])

                plt.figure()
                plt.plot(X1,Y1,label='PACE4',marker = 'o', ms = 3, color = 'green',linestyle = 'None')
                plt.plot(X2,Y2,label='Talys',marker = 'o', ms = 3, color = 'orange',linestyle = 'None')


                Title =  str(int(CN[3:6])-int(key[3:6]))+' evaporated neutrons'
                plt.title(Title)
                for author in rpEXFORData.keys():
                    if (key in rpEXFORData[author]):
                        plt.errorbar(rpEXFORData[author][key][0],rpEXFORData[author][key][1], yerr = rpEXFORData[author][key][2], label = author,marker = next(marker), color = next(color), ecolor='k', elinewidth=1, capsize=2,markersize = 2, linestyle = 'None' )
                plt.legend()
                plt.xlabel("Energy [MeV]")
                plt.ylabel("Cross Section [mb]")
                plt.xlim((10,150))
                plt.yscale('log')
                #plt.show()
                plt.savefig(outfile,dpi = 300)
                plt.close()


        elif choice == 3:
            clear()
            print(ascii_banner)
            subchoice = ''
            CN = ''
            CommonIsoKey = []

            while True:
                subchoice = input('Enter all for plotting everything\nEnter n for plotting only the neutron evaporated residuals\nEnter [ZZZAAA] for plotting a specific isotope : ')
                if (subchoice == 'all' or subchoice == 'n' or (len(subchoice) == 6)): break
                print(colored('WARNING :', 'yellow')," Wrong choice format")


            #-----sort produced istopes-----#
            if args.Talysfolder is not None:
                TalyskeyList = keysorter(rpTalysData)
            else:
                print(colored('ERROR :', 'red'), ' Talys Data not provided')
                raise SystemExit

            if args.PACEfolder is not None:
                PACEkeyList = keysorter(rpPACEData)
            else:
                print(colored('ERROR :', 'red'), ' PACE Data not provided')
                raise SystemExit


            if (subchoice == 'n'):
                while True:
                    CN = input('Insert CN [ZZZAAA] : ')
                    if (len(CN) == 6): break
                    print(colored('WARNING :', 'yellow')," Wrong CN format")
                for key in rpPACEData.keys():
                    if key in rpTalysData.keys():
                        if key[0:3] == CN[0:3]:
                            CommonIsoKey.append(key)

            elif (subchoice == 'all'):
                for key in rpPACEData.keys():
                    if key in rpTalysData.keys():
                        CommonIsoKey.append(key)
            elif (len(subchoice) == 6):
                CommonIsoKey.append(subchoice)

            try:
                os.mkdir(args.Outfolder+'/SIM')
            except:
                print(colored('WARNING :', 'yellow')," Simulation plot already exist. Content will be replaced")

            for key in CommonIsoKey:
                print('------Plotting production Cross Section for ',key,'------')
                outfile = args.Outfolder+'/SIM/'+key+'.png'
                plt.figure()
                #sorting
                X1, Y1 = listsorter(rpPACEData[key][0], rpPACEData[key][1])
                X2, Y2 = listsorter(rpTalysData[key][0], rpTalysData[key][1])

                plt.figure()
                plt.plot(X1,Y1,label='PACE4',marker = 'o', ms = 3, color = 'green',linestyle = 'None')
                plt.plot(X2,Y2,label='Talys',marker = 'o', ms = 3, color = 'orange',linestyle = 'None')
                if (subchoice == 'n'):
                    Title =  str(int(CN[3:6])-int(key[3:6]))+' evaporated neutrons'
                    plt.title(Title)
                plt.legend()
                plt.xlabel("Energy [MeV]")
                plt.ylabel("Cross Section [mb]")
                plt.xlim((10,150))
                plt.yscale('log')
                #plt.show()
                plt.savefig(outfile,dpi = 300)
                plt.close()

        elif choice == 4:
            clear()
            print(ascii_banner)
            #-----retrieve recoil information-----#
            recTalysData = dict()
            recPACEData = dict()
            if args.Talysfolder is not None:
                print('--Sorting ',colored('Talys', 'green'),' recoil information--')
                recTalysData = Talys_recExtractor(args.Talysfolder)
            else:
                print(colored('ERROR :', 'red'), ' Talys Data not provided')
                raise SystemExit

            if args.PACEfolder is not None:
                print('--Sorting ',colored('PACE', 'green'),' recoil information--')
                #recPACEData = PACE_recExtractor(args.PACEfolder)
            else:
                print(colored('ERROR :', 'red'), ' PACE Data not provided')
                raise SystemExit

            subchoice = ''
            CN = ''
            PACEIsoKey = []
            TalysIsoKey = []
            clear()
            print(ascii_banner)
            while True:
                subchoice = input('Enter all for plotting everything\nEnter n for plotting only the neutron evaporated residuals\nEnter [ZZZAAA] for plotting a specific isotope \nEnter range for plotting isotopes in a specific range:')
                if (subchoice == 'all' or subchoice == 'n' or subchoice == 'range' or (len(subchoice) == 6)): break
                print(colored('WARNING :', 'yellow')," Wrong choice format")

            if (subchoice == 'n'):
                while True:
                    CN = input('Insert CN [ZZZAAA] : ')
                    if (len(CN) == 6): break
                    print(colored('WARNING :', 'yellow')," Wrong CN format")

                for key in recPACEData.keys():
                    if key[0:3] == CN[0:3]: PACEIsoKey.append(key)
                for key in recTalysData.keys():
                    if key[0:3] == CN[0:3]: TalysIsoKey.append(key)

            elif (subchoice == 'range'):
                while True:
                    ISO1 = input('Insert lower range limit [ZZZAAA] : ')
                    if (len(ISO1) == 6): break
                    print(colored('WARNING :', 'yellow')," Wrong Isotope format")
                while True:
                    ISO2 = input('Insert top range limit [ZZZAAA] : ')
                    if (len(ISO2) == 6): break
                    print(colored('WARNING :', 'yellow')," Wrong Isotope format")



                for Z in range(int(ISO1[0:3]),int(ISO2[0:3])+1,1):
                    for A in range(int(ISO1[3:6]),int(ISO2[3:6])+1,1):
                        IsoKey = '{:03d}'.format(Z)+'{:03d}'.format(A)
                        if (IsoKey in recTalysData.keys()): TalysIsoKey.append(IsoKey)
                print(TalysIsoKey)

            elif (subchoice == 'all'):
                PACEIsoKey = keysorter(recPACEData)
                TalysIsoKey = keysorter(recTalysData)

            elif (len(subchoice) == 6):
                if (subchoice in recTalysData.keys()) : TalysIsoKey.append(subchoice)
                if (subchoice in recPACEData.keys()) : PACEIsoKey.append(subchoice)
            PACEIsoKey.sort()
            TalysIsoKey.sort()
            try:
                os.mkdir(args.Outfolder+'/RECSIM')
            except:
                print(colored('WARNING :', 'yellow')," Recoil spectra already exist. Content will be replaced")
            try:
                os.mkdir(args.Outfolder+'/RECSIM/Talys')
            except:
                print(colored('WARNING :', 'yellow')," Talys Recoil spectra already exist. Content will be replaced")
            try:
                os.mkdir(args.Outfolder+'/RECSIM/PACE')
            except:
                print(colored('WARNING :', 'yellow')," PACE Recoil spectra already exist. Content will be replaced")

            for key in TalysIsoKey:
                try:
                    os.mkdir(args.Outfolder+'/RECSIM/Talys/rec'+key)
                    print('---Creating rec'+key+' folder---')
                except:
                    print('---Creating rec'+key+' folder---')
                finally:
                    os.system('rm -r '+args.Outfolder+'/RECSIM/Talys/rec'+key)
                    os.mkdir(args.Outfolder+'/RECSIM/Talys/rec'+key)

            for key in PACEIsoKey:
                try:
                    os.mkdir(args.Outfolder+'/RECSIM/PACE/rec'+key)
                    print('---Creating rec'+key+' folder---')
                except:
                    print('---Creating rec'+key+' folder---')
                finally:
                    os.system('rm -r '+args.Outfolder+'/RECSIM/PACE/rec'+key)
                    os.mkdir(args.Outfolder+'/RECSIM/PACE/rec'+key)

            Elist = recTalysData[TalysIsoKey[0]].keys()

            for isokey in TalysIsoKey:
                Elist = list(set(recTalysData[isokey].keys()) & set(Elist))

            Elist.sort()
            print(Elist)
            for energykey in Elist:
                print('------Plotting Talys recoil spectra for ',energykey,' MeV proton------')
                plt.figure()
                outfile = args.Outfolder+'/RECSIM/Talys/E'+energykey+'.png'
                Title = 'Energy -> '+energykey+' MeV'
                plt.title(Title)
                plt.xlabel("Energy [MeV]")
                plt.ylabel("Counts [a.u.]")
                for isokey in TalysIsoKey:
                    X1, Y1 = listsorter(recTalysData[isokey][energykey][0], recTalysData[isokey][energykey][1])
                    El = element(int(isokey[0:3]))
                    label = isokey[3:6]+El.symbol
                    plt.plot(X1,Y1,label=label,marker = 'o', ms = 3 )#,linestyle = 'None')

                    #plt.hist(X1, bins=X1, weights=Y1, label=label, density = True)

                    #plt.yscale('log')
                    #plt.show()
                plt.legend()
                plt.xlim((0,2.5))
                plt.savefig(outfile,dpi = 300)
                plt.close()




            for isokey in PACEIsoKey:
                for energykey in recPACEData[isokey].keys():
                    outfile = args.Outfolder+'/RECSIM/PACE/rec'+isokey+'/'+isokey+'E'+energykey+'.png'
                    print('------Plotting PACE recoil spectra for ',isokey,' produced with ',energykey,' MeV proton------')
                    plt.figure()
                    plt.hist(recPACEData[isokey][energykey][0], bins = 30,density = True)
                    #plt.plot(X1,Y1,label='PACE',marker = 'o', ms = 3, color = 'green',linestyle = 'None')
                    El = element(int(isokey[0:3]))
                    Title = isokey[3:6]+El.symbol+' recoil. \n p energy = '+energykey+' MeV'
                    plt.title(Title)
                    plt.xlabel("Energy [MeV]")
                    plt.ylabel("Counts [a.u.]")
                    #plt.yscale('log')
                    #plt.show()
                    plt.savefig(outfile,dpi = 300)
                    plt.close()

            for isokey in TalysIsoKey:
                for energykey in recTalysData[isokey].keys():
                    outfile = args.Outfolder+'/RECSIM/Talys/rec'+isokey+'/'+isokey+'E'+energykey+'.png'
                    print('------Plotting Talys recoil spectra for ',isokey,' produced with ',energykey,' MeV proton------')

                    #sorting
                    X1, Y1 = listsorter(recTalysData[isokey][energykey][0], recTalysData[isokey][energykey][1])

                    plt.figure()
                    plt.hist(X1, bins=X1, weights=Y1, density = True)
                    #plt.plot(X1,Y1,label='Talys',marker = 'o', ms = 3, color = 'green',linestyle = 'None')
                    El = element(int(isokey[0:3]))
                    Title = isokey[3:6]+El.symbol+' recoil. \n p energy = '+energykey+' MeV'
                    plt.title(Title)
                    plt.xlabel("Energy [MeV]")
                    plt.ylabel("Counts [a.u.]")
                    #plt.yscale('log')
                    #plt.show()
                    plt.savefig(outfile,dpi = 300)
                    plt.close()







        elif choice == 5:
            clear()
            break

    # recTalysData = Talys_recExtractor(args.Talysfolder)
    #
    #
    # #-----sort PACE produced istopes-----#
    # PACEkeyList = []
    # for key in rpPACEData.keys():
    #     PACEkeyList.append(key)
    #
    # PACEkeyList.sort()
    #
    # PACEBIN = edgefinder(PACEkeyList)
    #
    #
    # #-----sort Talys produced istopes-----#
    # TalyskeyList = []
    # for key in rpTalysData.keys():
    #     TalyskeyList.append(key)
    #
    # TalyskeyList.sort()
    #
    # TalysBIN = edgefinder(TalyskeyList)
    #
    # #-----sort EXFOR experimental measured isotopes-----#
    # EXFORauthorList = []
    # EXFORIsokeyList = []
    # for key in rpEXFORData.keys():
    #     EXFORauthorList.append(key)
    #     for isokey in rpEXFORData[key].keys():
    #         if (isokey in EXFORIsokeyList): continue
    #         else: EXFORIsokeyList.append(isokey)
    #
    # EXFORauthorList.sort()
    # EXFORIsokeyList.sort()
    #
    # CommonIsoKey = []
    # for key in rpPACEData.keys():
    #     if key in rpTalysData:
    #         CommonIsoKey.append(key)
    #
    # CommonIsoKey.sort()
    #
    # CommonIsoKeyEXP = []
    # for key in rpPACEData.keys():
    #     if key in rpTalysData:
    #         if key in EXFORIsokeyList:
    #             CommonIsoKeyEXP.append(key)
    #
    # CommonIsoKeyEXP.sort()
    #
    # # ----make output directory for comparison
    # directory_name = args.Outfolder
    # try:
    #     os.mkdir(directory_name)
    # except:
    #     print("Warning:",directory_name,"Already exist. All content will be deleted.")
    #     print()
    # finally:
    #     os.system('rm -r '+directory_name)
    #     os.mkdir(directory_name)
    # #-----------printing recoil spectra------------------------
    # print('-------Drawing recoil spectra for the following isotopes-------')
    #
    # os.mkdir(directory_name+"/RECSIM")
    #
    # for isokey in recTalysData.keys():
    #     for energykey in recTalysData[isokey].keys():
    #         outfile = directory_name+'/RECSIM/rec'+isokey+'e'+energykey+'.png'
    #         print('Recoil -> '+isokey+' Energy -> '+energykey)
    #         #sorting
    #         X1, Y1 = sorter(recTalysData[isokey][energykey][0], recTalysData[isokey][energykey][1])
    #
    #         plt.figure()
    #         plt.plot(X1,Y1,label='Talys',marker = 'o', ms = 3, color = 'green',linestyle = 'None')
    #         El = element(int(isokey[0:3]))
    #         Title = isokey[3:6]+El.symbol+' recoil. \n p energy = '+energykey+' MeV'
    #         plt.title(Title)
    #         plt.xlabel("Energy [MeV]")
    #         plt.ylabel("Cross Section [mb]")
    #         #plt.yscale('log')
    #         #plt.show()
    #         plt.savefig(outfile,dpi = 300)
    #         plt.close()
    #
    #
    # #-----------printing comparison with exp data--------------
    # print('-------Drawing production cross sections for the following isotopes-------')
    #
    # os.mkdir(directory_name+"/EXPSIM")
    #
    # marker = itertools.cycle(('s', 'p', 'o'))
    # color = itertools.cycle(('m', 'b'))
    #
    # for key in CommonIsoKeyEXP:
    #     print(key)
    #     outfile = directory_name+'/EXPSIM/'+key+'.png'
    #     #sorting
    #     X1, Y1 = sorter(rpPACEData[key][0], rpPACEData[key][1])
    #     X2, Y2 = sorter(rpTalysData[key][0], rpTalysData[key][1])
    #
    #     plt.figure()
    #     plt.plot(X1,Y1,label='PACE4',marker = 'o', ms = 3, color = 'green',linestyle = 'None')
    #     plt.plot(X2,Y2,label='Talys',marker = 'o', ms = 3, color = 'orange',linestyle = 'None')
    #
    #
    #     Title =  str(int(args.CN[3:6])-int(key[3:6]))+' evaporated neutrons'
    #     plt.title(Title)
    #     for author in rpEXFORData.keys():
    #         if (key in rpEXFORData[author]):
    #             plt.errorbar(rpEXFORData[author][key][0],rpEXFORData[author][key][1], yerr = rpEXFORData[author][key][2], label = author,marker = next(marker), color = next(color), ecolor='k', elinewidth=1, capsize=2,markersize = 2, linestyle = 'None' )
    #     plt.legend()
    #     plt.xlabel("Energy [MeV]")
    #     plt.ylabel("Cross Section [mb]")
    #     plt.xlim((10,150))
    #     plt.yscale('log')
    #     #plt.show()
    #     plt.savefig(outfile,dpi = 300)
    #     plt.close()
    #
    # #---------SEGRE PLOT
    # os.mkdir(directory_name+"/SEGRESIM")
    # os.mkdir(directory_name+"/SEGRESIM/PACE")
    # os.mkdir(directory_name+"/SEGRESIM/Talys")
    # # ----plotting segre plot for Talys--------
    # print('plotting segre plot for Talys')
    # for energy in range(20,140,5):
    #
    #     N, Z, W = histolister(rpTalysData,energy)
    #     hist, xbins, ybins, im = plt.hist2d(N,Z,bins=TalysBIN, weights=W, cmap='autumn', norm=LogNorm(vmin=0.001, vmax=max(W)))
    #
    #     Title =  str(energy)+' MeV'
    #     outfile = directory_name+'/SEGRESIM/Talys/Energy_'+str(energy)+'.png'
    #
    #     plt.title(Title)
    #     plt.xlabel("N")
    #     plt.ylabel("Z")
    #
    #
    #     cbar = plt.colorbar()
    #     cbar.set_label("Cross Section [mb]")
    #     print('segree chart for energy -> ',energy)
    #     for i in range(len(ybins)-1):
    #         for j in range(len(xbins)-1):
    #             El = element(int(ybins[i]+0.5))
    #             label = str(int(xbins[j]+0.5+ybins[i]+0.5))+El.symbol
    #             if(hist.T[i,j]): plt.text(xbins[j]+0.5,ybins[i]+0.5, label, color="k", ha="center", va="center",fontsize = 4)
    #
    #     plt.savefig(outfile,dpi = 300)
    #     plt.close()
    #
    # # ----plotting segre plot for PACE--------
    # print('plotting segre plot for PACE')
    # for energy in range(20,140,5):
    #
    #     N, Z, W = histolister(rpPACEData,energy)
    #     hist, xbins, ybins, im = plt.hist2d(N,Z,bins=PACEBIN, weights=W, cmap='autumn', norm=LogNorm(vmin=0.001, vmax=max(W)))
    #
    #     Title =  str(energy)+' MeV'
    #     outfile = directory_name+'/SEGRESIM/PACE/Energy_'+str(energy)+'.png'
    #
    #     plt.title(Title)
    #     plt.xlabel("N")
    #     plt.ylabel("Z")
    #
    #
    #     cbar = plt.colorbar()
    #     cbar.set_label("Cross Section [mb]")
    #     print('segree chart for energy -> ',energy)
    #     for i in range(len(ybins)-1):
    #         for j in range(len(xbins)-1):
    #             El = element(int(ybins[i]+0.5))
    #             label = str(int(xbins[j]+0.5+ybins[i]+0.5))+El.symbol
    #             if(hist.T[i,j]): plt.text(xbins[j]+0.5,ybins[i]+0.5, label, color="k", ha="center", va="center",fontsize = 4)
    #
    #     plt.savefig(outfile,dpi = 300)
    #     plt.close()
    #
    # # #--------------plotting sim xsec-----------
    # # os.mkdir(directory_name+"/SIM")
    # #
    # # for key in CommonIsoKey:
    # #     print(key)
    # #     outfile = directory_name+'/SIM/'+key+'.png'
    # #     plt.figure()
    # #     plt.plot(rpPACEData[key][0],rpPACEData[key][1],label='PACE4',marker = 'v', color = 'green',linestyle = 'None')
    # #     plt.plot(rpTalysData[key][0],rpTalysData[key][1],label='Talys',marker = '8',color = 'orange',linestyle = 'None')
    # #     plt.legend()
    # #     plt.xlabel("Energy [MeV]")
    # #     plt.ylabel("Cross Section [mb]")
    # #     plt.xlim((10,150))
    # #     plt.yscale('log')
    # #     #plt.show()
    # #     plt.savefig(outfile,dpi = 300)
    # #     plt.close()


if __name__ == '__main__':
    main()