import os
from sys import exit
from shutil import move, rmtree
from hashlib import sha512
from re import findall
from time import time, sleep
try:
	os.chdir(os.path.abspath(os.path.dirname(__file__)))
except:
	pass
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EOF = (-1)
defaultTime = 5
cppFilepath  = "tests/protocol_tests.cpp"
buildFilepath = "build" # do not contain quotation marks
execFolderpath = "exe" # do not contain quotation marks and path separator
execFilename = "protocol_tests"
outputFilepath = "results.csv"
test_cases = list(range(3))
test_parameters = [(1 << i, None, None, None) for i in range(7)] + [(None, 1 << i, None, None) for i in range(7)] + [(None, None, 1 << i, None) for i in range(7)] # (N, n, m, index)


# handle #
def parseCpp(filepath = cppFilepath, encoding = "utf-8") -> dict:
	try:
		with open(filepath, "r", encoding = encoding) as f:
			content = f.read()
	except:
		return None
	blocks = content.replace("\r", "\n").split("\n")
	
	cut_index = []
	for i in range(len(blocks)):
		if blocks[i].startswith("BOOST_AUTO_TEST_CASE("):
			cut_index.append(i) # recond the head of each part
		elif blocks[i] == "BOOST_AUTO_TEST_SUITE_END()":
			cut_index.append(i) # recond the end of the cpp
	length = len(cut_index) # length is the count of the blocks plus 1
	if length < 1:
		return None
	
	block_dict = {"head":"\n".join(blocks[:cut_index[0]])}
	for i in range(length):
		if length - 1 == i:
			block_dict["tail"] = "\n".join(blocks[cut_index[i]:])
		else:
			block_dict[i] = "\n".join(blocks[cut_index[i]:cut_index[i + 1]])
	return block_dict

def compareFiles(fp1, fp2) -> bool:
	sha512_hash_1, sha512_hash_2 = sha512(), sha512()
	with open(fp1, "rb") as f:
		for chunk in iter(lambda:f.read(4096), b""):
			sha512_hash_1.update(chunk)
	with open(fp2, "rb") as f:
		for chunk in iter(lambda:f.read(4096), b""):
			sha512_hash_2.update(chunk)
	return sha512_hash_1.hexdigest() == sha512_hash_2.hexdigest()

def backup(cppFp = cppFilepath) -> bool:
	targetPath = "./" + os.path.split(cppFp)[1]
	if os.path.exists(targetPath):
		return os.path.isfile(targetPath) and compareFiles(cppFp, targetPath)
	try:
		move(cppFp, targetPath)
		return True
	except:
		return False

def test(i, parameter, cases, block_dict, cppFp = cppFilepath, buildFp = buildFilepath, execFp = execFolderpath, encoding = "utf-8") -> tuple:
	print("Handling Case {0} with (N = {1}, n = {2}, m = {3}, index = {4}). ".format(i, "default" if parameter[0] is None else parameter[0], "default" if parameter[1] is None else parameter[1], "default" if parameter[2] is None else parameter[2], "default" if parameter[3] is None else parameter[3]))
	try:
		with open(cppFilepath, "w", encoding = encoding) as f:
			f.write("#include <time.h>\n") # time.h
			f.write(block_dict["head"])
			f.write("\n")
			f.write(block_dict[i].replace(																						\
				"int N = ", ("int N = " if parameter[0] is None else "int N = {0}; // int N = ".format(parameter[0]))														\
			).replace(																								\
				"int n = ", ("int n = " if parameter[1] is None else "int n = {0}; // int n = ".format(parameter[1]))															\
			).replace(																								\
				"int m = ", ("int m = " if parameter[2] is None else "int m = {0}; // int m = ".format(parameter[2]))														\
			).replace(																								\
				"int index = ", ("int index = " if parameter[3] is None else "int index = {0}; // int index = ".format(parameter[3]))														\
			).replace(																								\
				"secp_primitives::GroupElement g;", "clock_t start_time = clock(); secp_primitives::GroupElement g;"														\
			).replace(																								\
				"sigma::SigmaPlusVerifier", "clock_t end_time = clock(); std::cout << \"Time consumption of generation: \" << (double(end_time - start_time) / CLOCKS_PER_SEC) << \"s\" << std::endl; start_time = clock(); sigma::SigmaPlusVerifier"		\
			).replace(																								\
				"\n}", "\n    end_time = clock(); std::cout << \"Time consumption of verification: \" << (double(end_time - start_time) / CLOCKS_PER_SEC) << \"s\" << std::endl;\n}"								\
			))
			f.write("\n")
			f.write(block_dict["tail"])
	except:
		print("Write to \"{0}\" failed. ".format(cppFp))
		return (False, None, None)
	if os.path.isdir(execFp):
		try:
			rmtree(execFp)
		except:
			print("Remove executable directory \"{0}\" failed. ".format(execFp))
			return (False, None, None)
	print("Executing: \"./{0}\" \"{1}\"".format(buildFp, execFp))
	os.system("\"./{0}\" \"{1}\"".format(buildFp, execFp))
	target = os.path.join(execFp, os.path.splitext(os.path.split(cppFp)[1])[0])
	if not os.path.isfile(target):
		print("Build executables failed. ")
		return (False, None, None)
	print("Executing: \"./{0}\"".format(target))
	with os.popen("\"./{0}\"".format(target)) as p:
		content = p.read()
	results = findall("\\d+\\.\\d+", content)
	if len(results) == 2:
		results = [float(results[0]), float(results[1])]
	else:
		return (False, None, None)
	print("The test of Case {0} with (N = {1}, n = {2}, m = {3}, index = {4}) is finished. ".format(i, "default" if parameter[0] is None else parameter[0], "default" if parameter[1] is None else parameter[1], "default" if parameter[2] is None else parameter[2], "default" if parameter[3] is None else parameter[3]))
	return (True, results[0], results[1])

def doTest(cases, block_dict, parameters = test_parameters, cppFp = cppFilepath, buildFp = buildFilepath, execFp = execFolderpath, outputFp = outputFilepath, encoding = "utf-8") -> int:
	if os.path.isfile(buildFp):
		os.system("chmod +x \"{0}\"".format(buildFp))
	else:
		print("Missing build file \"{0}\"".format(buildFp))
		return 0
	try:
		with open(outputFp, "w", encoding = encoding) as f:
			f.write("test case,N,n,m,index,Generation (s),Verification (s)\n")
	except:
		print("Open file \"{0}\" failed. ".format(outputFp))
	success_count = 0
	for i in cases:
		if i in block_dict:
			for parameter in parameters:
				t = test(i, parameter, cases, block_dict, cppFp = cppFp, buildFp = buildFp, execFp = execFp, encoding = encoding)
				if t[0]:
					try:
						with open(outputFp, "a", encoding = encoding) as f:
							f.write("{0},{1},{2},{3},{4},{5},{6}\n".format(i, "default" if parameter[0] is None else parameter[0], "default" if parameter[1] is None else parameter[1], "default" if parameter[2] is None else parameter[2], "default" if parameter[3] is None else parameter[3], t[1], t[2]))
						success_count += 1
					except:
						print("Write to file \"{0}\" failed. The failed line is as follows. ".format(outputFp))
						print("{0},{1},{2},{3},{4},{5},{6}\n".format(i, "default" if parameter[0] is None else parameter[0], "default" if parameter[1] is None else parameter[1], "default" if parameter[2] is None else parameter[2], "default" if parameter[3] is None else parameter[3], t[1], t[2]))
	return success_count

def restore(cppFp = cppFilepath) -> bool:
	sourcePath = "./" + os.path.split(cppFp)[1]
	if not os.path.isfile(sourcePath):
		return False
	try:
		if os.path.isfile(cppFp):
			os.remove(cppFp)
		move(sourcePath, cppFp)
		return True
	except:
		return False


# main function #
def preExit(countdownTime = defaultTime) -> None: # we use this function before exiting instead of getch since getch is not OS-independent
	try:
		cntTime = int(countdownTime)
		length = len(str(cntTime))
	except:
		return
	print()
	while cntTime > 0:
		print("\rProgram ended, exiting in {{0:>{0}}} second(s). ".format(length).format(cntTime), end = "")
		sleep(1)
		cntTime -= 1
	print("\rProgram ended, exiting in {{0:>{0}}} second(s). ".format(length).format(cntTime))

def main() -> int:
	block_dict = parseCpp()
	if block_dict is None:
		print("Error reading cpp file \"{0}\", please check. ".format(cppFilepath))
		preExit()
		exit(EOF)
	print("Get {0} test cases. ".format(len(block_dict) - 2)) # cut out the head and the tail
	if not backup(cppFilepath):
		print("Backup cpp file \"{0}\" failed. \nPlease check if a directory or a file with the same filename exists in the current path. ".format(cppFilepath))
		preExit()
		exit(EOF)
	success_count = doTest(test_cases, block_dict)
	total_count = len(test_cases) * len(test_parameters)
	print("Success / Total = {0} / {1} = {2:.2f}%. ".format(success_count, total_count, success_count * 100 / total_count))
	if not restore(cppFilepath):
		print("Restore cpp file \"{0}\" failed. \nPlease check if a directory or a file with the same filename exists in the current path. ".format(cppFilepath))
		preExit()
		exit(EOF)
	preExit()
	exit(EXIT_SUCCESS if success_count == total_count else EXIT_FAILURE)



if __name__ == "__main__":
	exit(main())