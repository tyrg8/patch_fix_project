import re
import os
from urllib.parse import unquote
import stat
import shutil
import subprocess
import json


input_filename="merge_C++_fix2.jsonl"
output_dir = "/mnt/sdb/cpp_files/"
linux_dir = "/mnt/sdb/cpp_files_check"
cache_bazel_dir="/home/xiaoran/.cache/bazel"
os.makedirs(output_dir, exist_ok=True)

cpu_count = os.cpu_count()

def fix_line_endings(folder_path):
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                subprocess.run(["dos2unix", file_path], check=True)
                print(f"Fixed: {file_path}")
            except subprocess.CalledProcessError as e:
                print(f"Error fixing {file_path}: {e}")
            except FileNotFoundError:
                print("dos2unix command not found. Please install it.")

def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            # Skip broken symbolic links
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
    return total_size

def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def copytree(project_path_gx,project_path_lx):
    os.makedirs(project_path_lx, exist_ok=True)
    for item in os.listdir(project_path_gx):
        source_item = os.path.join(project_path_gx, item)
        destination_item = os.path.join(project_path_lx, item)

        if os.path.isdir(source_item):
            shutil.copytree(source_item, destination_item, dirs_exist_ok=True)
        else:
            shutil.copy2(source_item, destination_item)
    print(f"{project_path_lx} copy done")

def find_makefiles1(folder_path):
    makefile_paths = []
    for root, dirs, files in os.walk(folder_path):
        if "Makefile" in files:
            makefile_paths.append(os.path.join(root, "Makefile"))
    return makefile_paths

def compile_project(makefile_path):
    dir = os.path.dirname(makefile_path)
    makefile_name = os.path.basename(makefile_path)
    try:
        subprocess.run(["bear", "--", "make", "-f", makefile_name, f"-j{cpu_count}"], cwd=dir, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False

def is_makefile(file_path):
    try:
        result = subprocess.run(["file", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return "makefile" in result.stdout.lower()
    except Exception:
        return False
    
def find_makefiles_2(folder_path, aim_file, file_index):
    makefile_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "makefile" or file.lower() == "makefile.dist" or file.lower() == "makefile.unix":
                makefile_path = os.path.join(root, file)
                print(f"{makefile_path} start")
                compile_success_1 = compile_project(makefile_path)
                if compile_success_1==False:
                    makefile_paths.append(makefile_path)
                    makefile_paths.append("?")
                    makefile_paths.append("?")
                    return makefile_paths
                print(f"{makefile_path} part1 success")
                makefile_paths.append(makefile_path)
                with open(os.path.join(root, "compile_commands.json"), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        makefile_paths.append("?")
                        return makefile_paths
    return makefile_paths

def find_makefiles_1(folder_path, aim_file, file_index):
    makefile_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            makefile_path = os.path.join(root, file)
            if is_makefile(makefile_path):
                print(f"{makefile_path} start")
                compile_success_1 = compile_project(makefile_path)
                if compile_success_1==False:
                    continue
                print(f"{makefile_path} part1 success")
                with open(aim_file, 'w') as file:
                    pass
                compile_success_0 = compile_project(makefile_path)
                if compile_success_1==True:
                    makefile_paths.append(makefile_path)
                    if compile_success_0==False:
                        makefile_paths.append("?")
                    return makefile_paths
    return makefile_paths
    
def find_cmakelists1(folder_path):
    makefile_paths = []
    for root, dirs, files in os.walk(folder_path):
        if "CMakeLists.txt" in files:
            makefile_paths.append(os.path.join(root, "CMakeLists.txt"))
    return makefile_paths

def compile_with_cmake(cmakelists_path):
    build_dir = os.path.join(os.path.dirname(cmakelists_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    # shutil.rmtree(build_dir, onerror=remove_readonly)
    # os.makedirs(build_dir, exist_ok=True)
    try:
        subprocess.run(["cmake", ".."], cwd=build_dir, check=True)
        subprocess.run(["bear", "--", "make", f"-j{cpu_count}"], cwd=build_dir, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False

def find_cmakelists(folder_path, aim_file, file_index):
    cmakelists_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "cmakelists.txt":
                cmakelists_path = os.path.join(root, file)
                print(f"{cmakelists_path} start")
                compile_success_1 = compile_with_cmake(cmakelists_path)
                if compile_success_1==False:
                    cmakelists_paths.append(cmakelists_path)
                    cmakelists_paths.append("?")
                    cmakelists_paths.append("?")
                    return cmakelists_paths
                print(f"{cmakelists_path} part1 success")
                cmakelists_paths.append(cmakelists_path)
                with open(os.path.join(root, os.path.join("build","compile_commands.json")), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        cmakelists_paths.append("?")
                        return cmakelists_paths
                
    return cmakelists_paths

def compile_dockerfile(dockerfile_path, image_name):
    success = 0
    dir = os.path.dirname(dockerfile_path)
    dockerfile_name = os.path.basename(dockerfile_path)
    try:
        subprocess.run(["docker", "build", "-f", dockerfile_name, "-t", image_name, "."],cwd=dir,check=True)
        print(f"build {image_name} success")
        success = 1
    except subprocess.CalledProcessError:
        print(f"build {image_name} fail")
    except OSError as e:
        print(f"OS error: {e}")
        return False
    try:
        subprocess.run("docker rm -f $(docker ps -aq)", shell=True, check=True)
        print("clean container success")
    except subprocess.CalledProcessError:
        print("clean container fail")
    except OSError as e:
        print(f"OS error: {e}")
        return False
    try:
        subprocess.run("docker rmi -f $(docker images -aq)", shell=True, check=True)
        print("clean container success")
    except subprocess.CalledProcessError:
        print("clean container fail")
    except OSError as e:
        print(f"OS error: {e}")
        return False
    if success==1:
        return True
    else:
        return False

def find_dockerfiles(folder_path, aim_file, file_index):
    dockerfile_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "dockerfile":
                dockerfile_path = os.path.join(root, file)
                print(f"{dockerfile_path} start")
                compile_success_1 = compile_dockerfile(dockerfile_path,"cve"+file_index.split("-")[-1])
                if compile_success_1==False:
                    continue
                print(f"{dockerfile_path} part1 success")
                with open(aim_file, 'w') as file:
                    pass
                compile_success_0 = compile_dockerfile(dockerfile_path,"cve"+file_index.split("-")[-1])
                if compile_success_1==True:
                    dockerfile_paths.append(dockerfile_path)
                    if compile_success_0==False:
                        dockerfile_paths.append("?")
                    return dockerfile_paths
    return dockerfile_paths
def compile_with_bazel(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    try:      
        print("bazel build ...")
        subprocess.run(["bazel","build"], cwd=dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        shutil.rmtree(cache_bazel_dir, onerror=remove_readonly)
        return False
    except OSError as e:
        shutil.rmtree(cache_bazel_dir, onerror=remove_readonly)
        print(f"OS error: {e}")
        return False
    
def find_bazel(folder_path, aim_file, file_index):
    bazel_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file in ("BUILD", "BUILD.bazel"):
                bazel_path = os.path.join(root, file)
    # for file in os.listdir(folder_path):  
    #     file_path = os.path.join(folder_path, file)
    #     if os.path.isfile(file_path):
    #         if file in ("BUILD", "BUILD.bazel"):
    #             bazel_path = file_path
                bazel_paths.append(bazel_path)
                compile_success_1 = compile_with_bazel(bazel_path)
                if compile_success_1==False:
                    bazel_paths.append("?")
                    bazel_paths.append("?")
                    return bazel_paths
                else:
                    bazel_paths.append("?")
                    return bazel_paths
    return bazel_paths

def compile_with_moz(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    build_dir = os.path.join(os.path.dirname(makefile_am_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    try:      
        print("../mach ...")
        try:
            subprocess.run(["git","fetch","origin"], cwd=build_dir, check=True)
            subprocess.run(["git","checkout","master"], cwd=build_dir, check=True)
            # git pull origin master
            subprocess.run(["git","pull","origin","master"], cwd=build_dir, check=True)
        except:
            print("no need pull")
        # subprocess.run(["../mach","bootstrap"], cwd=build_dir, check=True)
        subprocess.run(["../mach","configure"], cwd=build_dir, check=True)
        subprocess.run(["../mach","build"], cwd=build_dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False
    
def find_moz(folder_path, aim_file, file_index):
    moz_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "mach":
                moz_path = os.path.join(root, file)
    # for file in os.listdir(folder_path):  
    #     file_path = os.path.join(folder_path, file)
    #     if os.path.isfile(file_path):
    #         if file=="mach":
    #             moz_path = file_path
                moz_paths.append(moz_path)
                compile_success_1 = compile_with_moz(moz_path)
                if compile_success_1==False:
                    moz_paths.append("?")
                    moz_paths.append("?")
                    return moz_paths
                else:
                    moz_paths.append("?")
                    return moz_paths
    return moz_paths

def compile_with_configure(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    build_dir = os.path.join(os.path.dirname(makefile_am_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    try:      
        print("../configure ...")
        subprocess.run(["../configure"], cwd=build_dir, check=True)
        print("make ...")
        subprocess.run(["bear", "--", "make", f"-j{cpu_count}"], cwd=build_dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False



def find_configure(folder_path, aim_file, file_index):
    configure_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "configure":
                configure_path = os.path.join(root, file)
                compile_success_1 = compile_with_configure(configure_path)
                if compile_success_1==False:
                    configure_paths.append(configure_path)
                    configure_paths.append("?")
                    configure_paths.append("?")
                    return configure_paths
                print(f"{configure_path} part1 success")
                configure_paths.append(configure_path)
                with open(os.path.join(root, os.path.join("build","compile_commands.json")), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        configure_paths.append("?")
                        return configure_paths
    return configure_paths

def compile_with_am(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    build_dir = os.path.join(os.path.dirname(makefile_am_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    try:
        print("autoreconf -i ...")
        subprocess.run(["autoreconf", "-i"], cwd=dir, check=True)        
        print("../configure ...")
        subprocess.run(["../configure"], cwd=build_dir, check=True)
        print("make ...")
        subprocess.run(["bear", "--", "make", f"-j{cpu_count}"], cwd=build_dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False

def find_makefile_am(folder_path, aim_file, file_index):
    makefile_am_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "configure.ac":
                makefile_am_path = os.path.join(root, file)
                compile_success_1 = compile_with_am(makefile_am_path)
                if compile_success_1==False:
                    makefile_am_paths.append(makefile_am_path)
                    makefile_am_paths.append("?")
                    makefile_am_paths.append("?")
                    return makefile_am_paths
                print(f"{makefile_am_path} part1 success")
                makefile_am_paths.append(makefile_am_path)
                with open(os.path.join(root, os.path.join("build","compile_commands.json")), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        makefile_am_paths.append("?")
                        return makefile_am_paths
    return makefile_am_paths

def compile_with_meson(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    build_dir = os.path.join(os.path.dirname(makefile_am_path), "build")
    try:
        print("meson setup build ...")
        subprocess.run(["meson","setup","build"], cwd=dir, check=True)        
        print("ninja ...")
        subprocess.run(["ninja"], cwd=build_dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False
    
def find_meson(folder_path, aim_file, file_index):
    meson_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() in ["meson","meson.build"]:
                meson_path = os.path.join(root, file)
                meson_paths.append(meson_path)
                compile_success_1 = compile_with_meson(meson_path)
                if compile_success_1==False:
                    meson_paths.append("?")
                    meson_paths.append("?")
                    return meson_paths
                else:
                    meson_paths.append("?")
                    return meson_paths
    return meson_paths
    

def compile_with_autogen(makefile_am_path):
    dir = os.path.dirname(makefile_am_path)
    makefile_name = os.path.basename(makefile_am_path)
    build_dir = os.path.join(os.path.dirname(makefile_am_path), "build")
    os.makedirs(build_dir, exist_ok=True)
    try:
        print("./autogen.sh ...")
        subprocess.run(["./autogen.sh"], cwd=dir, check=True)        
        print("../configure ...")
        subprocess.run(["../configure"], cwd=build_dir, check=True)
        print("make ...")
        subprocess.run(["bear", "--", "make", f"-j{cpu_count}"], cwd=build_dir, check=True)
        print("done")
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError as e:
        print(f"OS error: {e}")
        return False

def find_autogen(folder_path, aim_file, file_index):
    autogen_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower() == "autogen.sh":
                autogen_path = os.path.join(root, file)
                compile_success_1 = compile_with_autogen(autogen_path)
                if compile_success_1==False:
                    autogen_paths.append(autogen_path)
                    autogen_paths.append("?")
                    autogen_paths.append("?")
                    return autogen_paths
                print(f"{autogen_path} part1 success")
                autogen_paths.append(autogen_path)
                with open(os.path.join(root, os.path.join("build","compile_commands.json")), 'r', encoding='utf-8') as f:
                    compile_commands = json.load(f)
                for entry in compile_commands:
                    if 'file' in entry and os.path.basename(aim_file) in os.path.basename(entry['file']):
                        print(f"find target {entry['file']}")
                        autogen_paths.append("?")
                        return autogen_paths
    return autogen_paths



one_file_num=361
try:
    with open("jilujilu.txt", "r",encoding = "utf-8") as r:
        jilu_str=r.readlines()[0]
    jilu=eval(jilu_str)
except:
    jilu=[0 for _ in range(one_file_num)]
try:
    with open("jilupath.txt", "r",encoding = "utf-8") as r:
        jilupath_str=r.readlines()[0]
    jilupath=eval(jilupath_str)
except:
    jilupath=["NULL" for _ in range(one_file_num)]
#0:copy fail 1:copy file 2:makefiles 3:cmakelists 4:neither 5:makefile succeed, but not required 6:cmakelists succeed, but not required 7:both succeed, but not required 8:docke succeed, but not required 9:dockerfile
timen0=0
with open("jilu.txt", "r",encoding = "utf-8") as r:
    time1_str=r.readlines()[0]
time1=eval(time1_str)

try:
    shutil.rmtree(linux_dir, onerror=remove_readonly)
except:
    print(f"no {linux_dir} excists")
finally:
    os.makedirs(linux_dir, exist_ok=True)

with open(input_filename, "r",encoding = "utf-8") as r:
    data_all = r.readlines()
    print(len(data_all))
    for data_one_str in data_all:
        if timen0==125 or timen0==126 or timen0==127:
            print(f"too big, jump {timen0}")
            jilu[timen0]=-1
            timen0+=1
            continue
        if timen0==200 or timen0==201 or timen0==202:
            print(f"need jiaohu, jump {timen0}")
            jilu[timen0]=-2
            timen0+=1
            continue
        if timen0==262 or timen0==263:
            print(f"no target, jump {timen0}")
            jilu[timen0]=-3
            timen0+=1
            continue
        # if timen0>=2:
        #     print(f"test, jump {timen0}")
        #     jilu[timen0]=-3
        #     timen0+=1
        #     continue
        #if timen0==3:
        #    break
        if time1[timen0]==0:
            print(f"jump {timen0}")
            timen0+=1
            continue
        else:
            print(f"--------{timen0} undone")
        # if jilu[timen0]!=0 and jilu[timen0]!=4:
        if jilu[timen0]!=0:
        # if jilu[timen0]!=0 and jilu[timen0]!=4 and jilu[timen0]<10:
        # if jilu[timen0]!=0 and jilu[timen0]!=4 and jilu[timen0]!=12:
            print(f"jump {timen0}")
            timen0+=1
            continue
        else:
            print(f"--------{timen0} undone")
        # if timen0!=19:
        #     print(f"test, jump {timen0}")
        #     jilu[timen0]=-3
        #     timen0+=1
        #     continue
        data_one=eval(data_one_str)
        raw_code=data_one["details"][0]["raw_code"]
        old_code=data_one["details"][0]["old_code"]
        patch=data_one["details"][0]["patch"]
        path=str(unquote(data_one["details"][0]["raw_url"].split('/')[-1]))
        url0=data_one["html_url"].split("/commit/")[0]
        commit_hash=data_one["html_url"].split("/commit/")[1]
        project_path_gx = os.path.join(output_dir, data_one["cve_id"]+'-'+str(data_one["index"]))
        project_path_lx = os.path.join(linux_dir, data_one["cve_id"]+'-'+str(data_one["index"]))
        file_index=data_one["cve_id"]+'-'+str(data_one["index"])
        aim_path = os.path.join(project_path_lx,path)
        print(aim_path)
        if not os.path.exists(project_path_lx):
            os.makedirs(project_path_lx)
        try:
            copytree(project_path_gx,project_path_lx)
        except Exception as e:
            print(f"Error copy: {e}")
            #time1[timen0]=0
            print(f"{project_path_lx} copy fail")
#1 get project done
        jilu[timen0]=1
        jilu_temp=[]
        jilupath_temp=[]
        step=1
        print("--------start bazel---------")
        bazel=find_bazel(project_path_lx,aim_path,file_index)
        if step==1:
            if len(bazel)==3:
                # jilu[timen0]=12
                jilu_temp.append(12)
                print(f"{project_path_lx} bazel fail")
                # jilupath[timen0]=bazel[0]
                jilupath_temp.append(bazel[0])
                print(bazel)
            elif len(bazel)==2:
                jilu_temp.append(2)
                print(f"{project_path_lx} bazel totally succeed")
                jilupath_temp.append(bazel[0])
                print(bazel)
                step=0
            else:
                jilu_temp.append(22)
                print(f"{project_path_lx} bazel unfound")
        if step==1:
            print("--------start moz---------")
            moz=find_moz(project_path_lx,aim_path,file_index)
            if len(moz)==3:
                jilu_temp.append(11)
                print(f"{project_path_lx} moz fail")
                jilupath_temp.append(moz[0])
                print(moz)
            elif len(moz)==2:
                jilu_temp.append(1)
                print(f"{project_path_lx} moz totally succeed")
                jilupath_temp.append(moz[0])
                print(moz)
                step=0
            else:
                jilu_temp.append(21)
                print(f"{project_path_lx} moz unfound")
        if step==1:
            print("--------start meson---------")
            meson=find_meson(project_path_lx,aim_path,file_index)
            if len(meson)==3:
                jilu_temp.append(13)
                print(f"{project_path_lx} meson fail")
                jilupath_temp.append(meson[0])
                print(meson)
            elif len(meson)==2:
                jilu_temp.append(3)
                print(f"{project_path_lx} meson totally succeed")
                jilupath_temp.append(meson[0])
                print(meson)
                step=0
            else:
                jilu_temp.append(23)
                print(f"{project_path_lx} meson unfound")
        if step==1:
            print("--------start configure---------")
            configure=find_configure(project_path_lx,aim_path,file_index)
            if len(configure)>=3 and configure[-2]=='?' and configure[-1]=='?':
                jilu_temp.append(19)
                print(f"{project_path_lx} configure fail")
                jilupath_temp.extend(configure[0:-2])
                print(configure)
            elif len(configure)>=2 and configure[-1]=='?':
                jilu_temp.append(9)
                print(f"{project_path_lx} configure totally succeed")
                jilupath_temp.extend(configure[0:-1])
                print(configure)
                step=0
            elif len(configure)>0:
                jilu_temp.append(39)
                print(f"{project_path_lx} configure useless")
                jilupath_temp.extend(configure)
                print(configure)
            else:    
                jilu_temp.append(29)
                print(f"{project_path_lx} configure unfound")
        if step==1:
            print("--------start makefile---------")
            makefile = find_makefiles_2(project_path_lx,aim_path,file_index)
            if len(makefile)>=3 and makefile[-2]=='?' and makefile[-1]=='?':
                jilu_temp.append(15)
                print(f"{project_path_lx} makefile fail")
                jilupath_temp.extend(makefile[0:-2])
                print(makefile)
            elif len(makefile)>=2 and makefile[-1]=='?':
                jilu_temp.append(5)
                print(f"{project_path_lx} makefile totally succeed")
                jilupath_temp.extend(makefile[0:-1])
                print(makefile)
                step=0
            elif len(makefile)>0:
                jilu_temp.append(35)
                print(f"{project_path_lx} makefile useless")
                jilupath_temp.extend(makefile)
                print(makefile)
            else:    
                jilu_temp.append(25)
                print(f"{project_path_lx} makefile unfound")
        if step==1:
            print("--------start cmake---------")
            cmakelists = find_cmakelists(project_path_lx,aim_path,file_index)
            if len(cmakelists)>=3 and cmakelists[-2]=='?' and cmakelists[-1]=='?':
                jilu_temp.append(16)
                print(f"{project_path_lx} cmakelists fail")
                jilupath_temp.extend(cmakelists[0:-2])
                print(cmakelists)
            elif len(cmakelists)>=2 and cmakelists[-1]=='?':
                jilu_temp.append(6)
                print(f"{project_path_lx} cmakelists totally succeed")
                jilupath_temp.extend(cmakelists[0:-1])
                print(cmakelists)
                step=0
            elif len(cmakelists)>0:
                jilu_temp.append(36)
                print(f"{project_path_lx} cmakelists useless")
                jilupath_temp.extend(cmakelists)
                print(cmakelists)
            else:    
                jilu_temp.append(26)
                print(f"{project_path_lx} cmakelists unfound")
        if step==1:
            print("--------start makefile_am---------")
            makefile_am = find_makefile_am(project_path_lx,aim_path,file_index)
            if len(makefile_am)>=3 and makefile_am[-2]=='?' and makefile_am[-1]=='?':
                jilu_temp.append(17)
                print(f"{project_path_lx} makefile_am fail")
                jilupath_temp.extend(makefile_am[0:-2])
                print(makefile_am)
            elif len(makefile_am)>=2 and makefile_am[-1]=='?':
                jilu_temp.append(7)
                print(f"{project_path_lx} makefile_am totally succeed")
                jilupath_temp.extend(makefile_am[0:-1])
                print(makefile_am)
                step=0
            elif len(makefile_am)>0:
                jilu_temp.append(37)
                print(f"{project_path_lx} makefile_am useless")
                jilupath_temp.extend(makefile_am)
                print(makefile_am)
            else:    
                jilu_temp.append(27)
                print(f"{project_path_lx} makefile_am unfound")
        if step==1:
            print("--------start autogen---------")
            autogen = find_autogen(project_path_lx,aim_path,file_index)
            if len(autogen)>=3 and autogen[-2]=='?' and autogen[-1]=='?':
                jilu_temp.append(18)
                print(f"{project_path_lx} autogen fail")
                jilupath_temp.extend(autogen[0:-2])
                print(autogen)
            elif len(autogen)>=2 and autogen[-1]=='?':
                jilu_temp.append(8)
                print(f"{project_path_lx} autogen totally succeed")
                jilupath_temp.extend(autogen[0:-1])
                print(autogen)
                step=0
            elif len(autogen)>0:
                jilu_temp.append(38)
                print(f"{project_path_lx} autogen useless")
                jilupath_temp.extend(autogen)
                print(autogen)
            else:    
                jilu_temp.append(28)
                print(f"{project_path_lx} autogen unfound")
        if step==1:
            jilu_temp.append(4)
        jilu[timen0]=jilu_temp
        jilupath[timen0]=jilupath_temp
        step=1
        

#ALL IS DONE
        shutil.rmtree(project_path_lx, onerror=remove_readonly)
        print(f"{project_path_lx} all is done,delete")
        timen0+=1
        with open("jilujilu.txt", 'w', encoding='utf-8') as file:
            file.write(str(jilu))
        with open("jilupath.txt", 'w', encoding='utf-8') as file:
            file.write(str(jilupath))
